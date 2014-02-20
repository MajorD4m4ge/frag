__author__ = 'khanta'
#TODO Check different filesizes and files
#TODO Check filename reading in directory
#TODO TimeDate Stamp MS and Accessed Day
#TODO Error checking on Volume
#TODO Windows won't work.
#TODO Add marking clusters as bad
#TODO Rework command line args
import os
import sys
import argparse
import datetime
import signal
import struct
import hashlib
from array import array
from sys import platform as _platform
import ntpath

debug = 0
error = ''
#References Microsoft's FAT General Overview 1.03 
# <editor-fold desc="Boot Sector Variables">

BytesPerSector = ''  #Offset 11 - 2 bytes
SectorsPerCluster = ''  #Offset 13 - 1 byte
ReservedSectorCount = ''  #Offset 14 - 2 bytes
NumberOfFATs = ''  #Offset 16 - 1 byte
TotalSectors = ''  #Offset 32 - 4 bytes
# Start of FAT32 Structure 
FAT32Size = ''  #Offset 36 - 4 bytes
RootCluster = ''  #Offset 44 - 4 bytes
FSInfoSector = ''  #Offset 48 - 2 bytes
ClusterSize = ''
TotalFAT32Sectors = ''
TotalFAT32Bytes = ''
DataAreaStart = ''
DataAreaEnd = ''
RootDirSectors = 0  #Always 0 for Fat32 Per MS Documentation
#FSINFO 
Signature = ''
NumberOfFreeClusters = 0
NextFreeCluster = 0
# </editor-fold>

# <editor-fold desc="Global Variables">
FirstChar = ''
EightDotThree = ''
FileAttributes = ''
CreatedTimeTenths = ''
CreateTimeHMS = ''
CreateDay = ''
AccessDay = ''
WrittenTimeHMS = ''
WrittenDay = ''
SizeOfFile = ''
FileSize = 0
HighTwoBytesFirst = ''
LowTwoBytesFirst = ''
FreeDirOffset = ''
#EndOfChain = 0xfffffff8
EndOfChain = 0x0fffffff
EndOfFile = 0x0fffffff
EmptyCluster = 0x00000000
DamagedCluster = 0x0ffffff7
ValidBytesPerSector = [512, 1024, 2048, 4096]

TotalChunks = 0  #The total clusters that need to be written. This will be int * remainder
FirstCluster = 0  #The first cluster.  This is written to the RootDir
ChunkList = []

MD5HashValue = ''

# </editor-fold>


def HashMD5(file, block_size=2 ** 20):
    if (debug >= 1):
        print('Entering HashMD5:')
    md5 = hashlib.md5()
    with open(file, 'rb') as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


def GetDate():
    if (debug >= 1):
        print('Entering GetDate:')
    dtm = datetime.datetime.now()
    #dtm = datetime.datetime.now()
    i_year = int((dtm.year - 1980) << 9)
    i_month = int((dtm.month) << 5)
    i_day = int((dtm.day & 0x1F))
    i_hour = int((dtm.hour) << 11)
    i_min = int((dtm.minute) << 5)
    i_sec = int(dtm.second) / 2
    i_ms = int(dtm.microsecond)
    i_lo = int((int(i_year) | int(i_month)) | int(i_day))
    i_hi = int((int(i_hour) | int(i_min)) | int(i_sec))
    low = struct.pack("<H", i_lo)
    high = struct.pack("<H", i_hi)
    #ms = struct.pack("h", i_ms)
    if (debug >= 2):
        print('MS:HH:MM:SS:DD - ' + str(high) + str(low))
    return high + low


def GetDay():
    if (debug >= 2):
        print('Entering GetDay:')
    dtm = datetime.datetime.now()
    i_day = int((dtm.day) & 0x1F)
    day = struct.pack(">i", i_day)
    if (debug >= 2):
        print('Day: ' + str(day))
    return day


def GetHighBytes(number):
    if (debug >= 2):
        print('Entering GetHighBytes:')
    highbytes = (number & 0xffff0000)
    if (debug >= 2):
        print('\tHigh Bytes: ' + str(highbytes))
    return highbytes


def GetLowBytes(number):
    if (debug >= 2):
        print('Entering GetLowBytes:')
    lowbytes = (number & 0x0000ffff)
    if (debug >= 2):
        print('\tLow Bytes: ' + str(lowbytes))
    return lowbytes


# def FileNamePad(file):
#     if (debug >= 1):
#         print('Entering FileNamePad:')
#     padding = 0
#     filename = file.replace('.', ' ')
#     if (len(file) < 11):
#         padding = 11 - len(file)
#
#     if (debug == 2):
#         print ('\tFilename : Replaced Filename --> ' + str(file) + ':' + str(file.replace('.', ' ')))
#
#     filename = filename.encode('ascii').upper()
#     filename += padding * b'\x20'
#     if (debug >= 2):
#         print('\tFilename Length/Padding Length: ' + str(len(file)) + '/' + str(padding))
#         print('\tFilename: ' + str(filename))
#     return filename


def FileNamePad(file):
    try:
        if (debug >= 1):
            print('Entering FileNamePad:')
        if (debug >= 2):
            print('\tFilename Passed in: ' + str(file))
        padding = 0
        length = len(file)
        if (length == 12):
            if "." in str(file):
                filename = file.replace('.', '')
                filename = filename.encode('ascii').upper()
                return filename
            else:
                print('Long Filenames not Supported.')
                sys.exit()
        else:
            if (length > 12):
                print('Long Filenames not Supported.')
                sys.exit()
            else:
                if "." in str(file):
                    if (debug >= 2):
                        print('\tFilename has Period in it.' + str(file))
                    filename = file.replace('.', ' ')
                    extension = filename[-3:]
                    filename1 = filename.split(' ')[0]
                    if (len(filename1) < 7):
                        padding = 7 - len(filename1)
                        if (debug >= 2):
                            print('\tFilename and Length - ' + str(filename1) + ' : ' + str(padding))
                        filename = filename1.encode('ascii').upper()
                        filename += padding * b'\x20'
                    else:
                        filename = file.encode('ascii').upper()
                else:
                    filename = file.encode('ascii').upper()

        extension = extension.encode('ascii').upper()
        if (debug >= 2):
            print('\tFilename Length/Padding Length: ' + str(len(file)) + '/' + str(padding))
            print('\tFilename: ' + str(filename + extension))
        filename = filename + extension
        return filename
    except:
        sys.exit('Error Verifying Filename.')



def ReadBootSector(volume):
    global DataAreaStart
    if (debug >= 1):
        print('Entering ReadBootSector:')
    # Reads the specified bytes from the drive
    try:
        with open(volume, "rb") as f:
            bytes = f.read(512)
            # <editor-fold desc="Global Variables">
            global BytesPerSector
            global BytesPerSector
            global SectorsPerCluster
            global ReservedSectorCount
            global NumberOfFATs
            global TotalSectors
            # Start of FAT32 Structure
            global FAT32Size
            global RootCluster
            global FSInfoSector
            global ClusterSize
            global BootSector
            global TotalFAT32Sectors
            global TotalFAT32Bytes
            global DataAreaStart
            global DataAreaEnd
            global FirstDataSector
            # </editor-fold>
            BytesPerSector = struct.unpack("<H", bytes[11:13])[0]
            if (BytesPerSector not in ValidBytesPerSector):
                print('Error: This is not a FAT32 drive.')
            SectorsPerCluster = struct.unpack("<b", bytes[13:14])[0]
            ReservedSectorCount = struct.unpack("<H", bytes[14:16])[0]
            NumberOfFATs = struct.unpack("<b", bytes[16:17])[0]
            TotalSectors = struct.unpack("i", bytes[32:36])[0]
            FAT32Size = struct.unpack("i", bytes[36:40])[0]
            RootCluster = struct.unpack("i", bytes[44:48])[0]
            FSInfoSector = struct.unpack("<H", bytes[48:50])[0]

            #Calculate some values
            ClusterSize = SectorsPerCluster * BytesPerSector
            TotalFAT32Sectors = FAT32Size * NumberOfFATs
            TotalFAT32Bytes = FAT32Size * 512

            DataAreaStart = ReservedSectorCount + TotalFAT32Sectors
            DataAreaEnd = TotalSectors - 1
            #Double Check per MS Documentation
            #FirstDataSector = BPB_ReservedSecCnt + (BPB_NumFATs * FATSz) + RootDirSectors;
            FirstDataSector = ReservedSectorCount + (NumberOfFATs * FAT32Size) + RootDirSectors
            if (debug >= 1):
                print('\tBytes per Sector: ' + str(BytesPerSector))
                print('\tSectors per Cluster: ' + str(SectorsPerCluster))
                print('\tCluster Size: ' + str(ClusterSize))
                print('\tRoot Cluster: ' + str(RootCluster))
                print('\tFSInfo Cluster: ' + str(FSInfoSector))
                print('\tTotal Sectors: ' + str(TotalSectors))
                print('\tReserved Sector Count: ' + str(ReservedSectorCount))
                print('\tReserved Sectors: ' + '0  - ' + str(ReservedSectorCount - 1))
                print('\tFAT Offset: ' + str(ReservedSectorCount))
                print('\tFAT Offset (Bytes): ' + str(ReservedSectorCount * 512))
                print('\tNumber of FATs: ' + str(NumberOfFATs))
                print('\tFAT32 Size: ' + str(FAT32Size))
                print('\tTotal FAT32 Sectors: ' + str(TotalFAT32Sectors))
                print('\tFAT Sectors: ' + str(ReservedSectorCount) + ' - ' + str(
                    (ReservedSectorCount - 1) + (FAT32Size * NumberOfFATs)))
                print('\tData Area: ' + str(DataAreaStart) + ' - ' + str(DataAreaEnd))
                print('\tData Area Offset (Bytes): ' + str(DataAreaStart * 512))
                print('\tRoot Directory: ' + str(DataAreaStart) + ' - ' + str(DataAreaStart + 3))
                #Extra Testing
                print('\t   First Data Sector: ' + str(FirstDataSector))
    except IOError:
        sys.exit('Error: Volume ' + str(volume) + ' does not exist.')
    except:
        sys.exit('Error: Cannot read Boot Sector.')


def GetFSInfo(volume):
    #try:
        if (debug >= 1):
            print('Entering GetFSInfo:')

        #Number of Free Clusters - 488-491
        #Next Free Cluster 492-495
        global NumberOfFreeClusters

        with open(volume, "rb") as f:
            f.seek(FSInfoSector * BytesPerSector + 488)
            temp = f.read(4)
            NumberOfFreeClusters = struct.unpack("<i", temp)[0]
            if (debug >= 2):
                print ('\tNumber of Free Clusters: ' + str(struct.unpack("<i", temp)[0]))
            f.seek(FSInfoSector * BytesPerSector + 492)
            NextFreeCluster = f.read(4)
            if (debug >= 2):
                print ('\tNext Free Cluster: ' + str(struct.unpack("<i", NextFreeCluster)[0]))
    #except:


def GetNextFreeCluster(volume):
    #try:
        if (debug >= 1):
            print('Entering GetNextFreeCluster:')

        global NextFreeCluster
        clusternumber = 0
        x = 0
        with open(volume, "rb") as f:
            f.seek(ReservedSectorCount * 512)  #Remember to multiply by 512 to get bytes
            bytes = f.read(TotalFAT32Bytes)  #Read a copy of the FAT Table
            #for u in range(0, chunks):
            while (True):
                temp = (bytes[x:x + 4])
                if (temp == b'\x00\x00\x00\x00'):
                    if (debug >= 2):
                        print('\tFree Cluster - Byte Offset: ' + str((ReservedSectorCount * 512) + x))
                        print('\tFree Cluster Number: ' + str(clusternumber))
                    freecluster = clusternumber
                    break
                else:
                    x += 4
                    clusternumber += 1
        NextFreeCluster = freecluster
        return freecluster
    #except:


def GetFileSize(file):
    if (debug >= 2):
        print('Entering GetFileSize:')
    size = os.path.getsize(file)  #Return length of file
    if (debug >= 2):
        print('\tFilesize: ' + str(size))
    return size


def MinFileLength(file, fragments):
    if (GetFileSize(file) < BytesPerSector * SectorsPerCluster * fragments + 1 ):
        return False
    else:
        return True


def GetOffsetFromCluster(FATOffset, cluster):  #FATOffset is ReservedSectorCount
    if (debug >= 2):
        print('Entering GetOffsetFromCluster:')
    temp = ((FATOffset * 512) + ((cluster) * 4))
    if (debug >= 2):
        print('\tFAT Offset: ' + str(FATOffset))
        print('\tFAT Offset (Bytes:) ' + str(FATOffset * 512))
        print('\tCluster: ' + str(cluster) + ' - Offset (Bytes): ' + str(temp))
    return (temp)


def GetChunks(file):
    try:
        if (debug >= 1):
            print('Entering GetChunks:')
        global TotalChunks
        totalchunks = (int)(GetFileSize(file) / ClusterSize)
        remainderbytes = GetFileSize(file) % ClusterSize
        if (remainderbytes == 0):  #Checks if there is a remainder, if so add an extra chunk to total
            if (totalchunks == 0):  #Fits in one cluster
                totalchunks = 1
            TotalChunks = totalchunks
        else:
            TotalChunks = totalchunks + 1
        if (debug >= 2):
            print('\t' + str(totalchunks) + ' - ' + str(ClusterSize) + ' byte chunks.')
            print('\tRemainder Bytes: ' + str(remainderbytes))
            print('\tOriginal File Size: ' + str(GetFileSize(file)))
            print('\tTotal Bytes to be Written: ' + str(totalchunks * ClusterSize + remainderbytes))
            print('\tTotal Chunks: ' + str(TotalChunks))
        return TotalChunks
    except:
        sys.exit('Error: Cannot Calculate Fragments.')


def ReadFat(volume, FATOffset, chunks, fragments):  #Passes in the volume and chunks that need to written
    #try:
        if (debug >= 1):
            print('Entering ReadFat:')
            print('\tChunks passed in: ' + str(chunks))
            print('\tFragment passed in: ' + str(fragments))
        global ChunkList
        global FirstCluster
        global TotalFreeClusters
        global NumberOfFreeClusters
        splitter = int(0)
        frag = False
        if (fragments != 0):
            frag = True
            if (debug >= 1):
                print('\tFragment Parameter Entered.')
        #print (frag)
        x = 0
        if (frag):
            splitter = int(chunks / fragments)  #The number of groups.  Divide by fragments and take integer
            if (debug >= 1):
                print('\tFragging Enabled.')
        numberofsplits = fragments - 1  #This is how many actual splits there will be
        counter = 0  #The counter to make sure we don't exceed the number of splits
        splitcounter = 0  #How many splits have occurred.
        if (debug >= 1):
            if (fragments != 0):
                print('\tSplitter Value: ' + str(splitter))
                print('\tTotal Number of Splits: ' + str(numberofsplits))
                print('\tFragment passed in: ' + str(fragments))
        with open(volume,
                  "rb") as f:  #Opens the file for reading/writing http://www.tutorialspoint.com/python/python_files_io.htm
            f.seek(FATOffset * 512)  #Remember to multiply by 512 to get bytes
            bytes = f.read(TotalFAT32Bytes)  #Read a copy of the FAT Table
            clusternumber = 0

            #for u in range(0, chunks):
            while (chunks != 0):
                temp = (bytes[x:x + 4])
                if (debug >= 2):
                    print('\tBytes Found: ' + str(x) + ':' + str(temp))
                    print('\tCluster Offset: ' + str(clusternumber))  #Clusters start at 2 , so add 2 to iterator
                if (temp == b'\x00\x00\x00\x00'):
                    if (debug >= 2):
                        print('\tFree Cluster - Byte Offset: ' + str((FATOffset * 512) + x))
                    ChunkList.append(clusternumber)
                    chunks -= 1
                    #Increase cluster number to force fragmentation (Future will be a frag counter that decrements here and then stops the increase once decremented
                    if (frag):
                        if (counter % splitter == 0):
                            if (debug >= 2):
                                print('\tCounter / Splitter: True')
                            if (numberofsplits > splitcounter):
                                clusternumber += 1
                                splitcounter += 1
                                x += 4
                                if (debug >= 2):
                                    print('\tSplit! SplitCounter \ Cluster: ' + str(splitcounter) + str(clusternumber))
                        else:
                            if (debug >= 2):
                                print('\tNo Fragmentation.')
                x += 4
                clusternumber += 1
            if (debug >= 1):
                print('\tCluster List [Total]: ' + '[' + str(len(ChunkList)) + ']' + (str(ChunkList)))

            FirstCluster = ChunkList[0]
            if (debug >= 2):
                print ('\tNumber of Free Clusters - Number Used (' + str(NumberOfFreeClusters) + ' - ' + str(len(ChunkList)) + ')' + '= ' + str(NumberOfFreeClusters - len(ChunkList)))
            NumberOfFreeClusters = NumberOfFreeClusters - len(ChunkList)
            if (debug >= 1):
                print('\tFirst Cluster: ' + (str(FirstCluster)))
                print('\tFirst Cluster Offset (Bytes:) ' + str(((FATOffset * 512) + ((FirstCluster - 1) * 4))))
    #except:
        #sys.exit('Error: Cannot read FAT.')


def ReadDirectory(volume, file):
    try:
        if (debug >= 1):
            print('Entering ReadDirectory:')
        #512 Bytes per sector * start sector
        global FreeDirOffset
        global error
        write = True
        if (SearchDirectory(volume, file, write)):
            error = 'File Exists in Directory.'
            sys.exit(1)
        with open(volume, "rb") as f:
            f.seek(512 * FirstDataSector)
            x = 0
            while True:
                f.seek(512 * FirstDataSector + x)
                bytes = f.read(32)  #Size of FAT32 Directory
                #FirstChar = struct.unpack("b", bytes[0:1])[0]
                if (bytes[0:1] == b'\xe5') or (bytes[0:1] == b'\x00'):
                    #if FirstChar in ('0x00', '0xe5'):
                    FreeDirOffset = ((512 * FirstDataSector) + x)
                    if (debug >= 1):
                        print('\tFirst Unallocated Directory Entry (Bytes): ' + str(FreeDirOffset))
                    break
                else:
                    x += 32
            return FreeDirOffset
    except:
        sys.exit('Error: ' + str(error))


def WriteDirectory(file, volume, unallocatedoffset, firstcluster):
    try:
        if (debug >= 1):
            print('Entering WriteDirectory:')
        s1 = FileNamePad(ntpath.basename(file))  #Writing Filename
        t1 = array("B", s1)
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 0)
            f.write(t1)

        s2 = b'\x20\x00\x08\x4E\x50\x49\x44\x49\x44'  #Adding archive bit and static info on time.
        t2 = array("B", s2)
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 11)
            f.write(t2)
        #Start Date Time
        sd = GetDate()  #Created Date/Time
        td = array("B", sd)
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 14)
            f.write(td)
        #End Date Time

        s3 = struct.pack("<H", GetHighBytes(firstcluster))  #High Bytes - 2 Bytes
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 20)
            f.write(s3)

        s4 = b'\x45\x50\x49\x44'  #static info on time.
        t4 = array("B", s4)
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 22)
            f.write(t4)

        #Start Date Time
        sd1 = GetDate()  #Written Date/Time
        td1 = array("B", sd1)
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 22)
            f.write(td1)
        #End Date Time

        s5 = struct.pack("<H", GetLowBytes(firstcluster))  #Low Bytes - 2 Bytes
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 26)
            f.write(s5)

        filesize = struct.pack("I", GetFileSize(file))  #Writing 4 bytes for file size
        with open(volume, "rb+") as f:  #Writing Binary!
            f.seek(unallocatedoffset + 28)
            f.write(filesize)
    except:
        sys.exit('Error: Cannot read Write Directory.')


def WriteFAT(volume, FATOffset, clusterlist):
    try:
        if (debug >= 1):
            print('Entering WriteFAT:')
        #clusterlist.pop(0) #Remove first entry in the clusterlist as that is the "First Cluster"
        if (debug >= 1):
            print('\tCluster List (Modified): ' + str(clusterlist))
        with open(volume, "rb+") as f:  #Opens the file for reading/writing http://www.tutorialspoint.com/python/python_files_io.htm
            f.seek(FATOffset * 512 + ((FirstCluster - 1) * 4))  #Remember to multiply by 512 to get bytes
            if (debug >= 1):
                print('\tSeeking to First Cluster Offset (Bytes): ' + str(FATOffset * 512 + ((FirstCluster - 1) * 4)))
            for cluster in clusterlist:
                c = struct.pack("I", cluster)
                f.write(c)
                f.seek(GetOffsetFromCluster(FATOffset, cluster))
            f.write(struct.pack("I", EndOfChain))
    except:
        sys.exit('Error: Cannot read Write FAT.')


def WriteData(volume, file, clusterlist):
    try:
        if (debug >= 1):
            print('Entering WriteData:')
        chunk = ''
        #Write data off of Data Section - Each Cluster is 2048 bytes and it starts at Cluster 2
        #Each cluster is 2048 bytes
        #clusterlist.insert(0, FirstCluster) #Adding First Cluster back in
        with open(volume, "rb+") as f:  #Opens the file for reading/writing http://www.tutorialspoint.com/python/python_files_io.htm
            if (debug >= 1):
                print('Opening Volume: ' + str(volume))
            with open(file, "rb") as r:
                if (debug >= 1):
                    print('\tReading file: ' + str(ntpath.basename(file)))
                for cluster in clusterlist:  #New Offset is 2 (Cluster)
                    seeker = (cluster * ClusterSize + (DataAreaStart * 512) - 2 * ClusterSize)
                    f.seek(seeker)  #Each ClusterNum - 2 (Offset) * Bytes per cluster + (DataAreaStart * 512)
                    if (debug >= 1):
                        print('\tSeeking to Cluster (Bytes) [Cluster]: ' + '[' + str(cluster) + ']' + str(seeker))
                    chunk = r.read(ClusterSize)
                    if (debug >= 2):
                           print('\tData Chunk Written: ' + str(chunk))
                    f.write(chunk)
        if (debug >= 1):
            print('\tCompleted Writing Data.')
    except:
        sys.exit('Error: Cannot Write Data.')


def SearchDirectory(volume, file, write):
        if (debug >= 1):
            print('Entering SearchDirectory:')
        s1 = FileNamePad(ntpath.basename(file))
        if (debug >= 2):
            print ('\tFilename to Search: ' + str(s1))
        match = False
        global FirstCluster
        global FileSize
        global e
        with open(volume, "rb") as f:
            if (debug >= 2):
                print('\tSeeking to First Data Sector [Bytes]: ' + str(512 * FirstDataSector))
            x = 0
            while (True):
                f.seek(512 * FirstDataSector + x)
                bytes = f.read(32)  #Size of FAT32 Directory
                FirstChar = struct.unpack("b", bytes[0:1])[0]
                if not (FirstChar == 0x00): #Check for Unallocated Dir (This means exit!)
                    if not (FirstChar == 0xe5): #Check for Unallocated Dir
                        filename = bytes[0:11]
                        if (debug >= 3):
                            print('\tFirst Character not 0xe5 or 0x00.')
                            print('\tReading First 11 Bytes.')
                            print ('\tDirectory Value: ' + str(filename))
                        if (filename == s1):
                            match = True
                            if (debug >= 3):
                                print ('\tFound Value That Matched: ' + str(s1))
                            if not (write):
                                ba = bytearray(bytes[26:28])
                                ba += bytes[20:22]
                                if (debug >= 2):
                                    print ('\tHigh/Low Bytes Bytearray [Length]: ' + '[' + str(len(ba)) + ']' + str(ba))
                                FirstCluster = struct.unpack("<i", ba)[0]
                                if (debug >= 1):
                                    print ('\tFirst Cluster: ' + str(FirstCluster))
                                ba1 = bytearray(bytes[28:32])
                                FileSize = struct.unpack("<i", ba1)[0]
                                if (debug >= 2):
                                    print ('\tFilesize Located in Directory [Bytes]: ' + str(FileSize))
                            else:
                                return match
                            break
                        else:
                            x += 32
                    else:
                        break
                else:
                    break


def SearchFAT(volume, FATOffset, FirstCluster):
    try:
        if (debug >= 1):
            print('Entering SearchFAT:')
            print('\tFirstCluster passed in: ' + str(FirstCluster))
            print('\tVolume passed in: ' + str(volume))
        readclusterlist = []
        nextcluster = FirstCluster
        readclusterlist.append(nextcluster)
        y = 0
        with open(volume, "rb") as f:
            f.seek(FATOffset * 512)
            bytes = f.read(TotalFAT32Bytes)
            if (debug >= 2):
                print('\tSeeking to FAT Offset (Bytes): ' + str(FATOffset * 512))
            while (y <= TotalFAT32Bytes):
                y += 4
                chunk = bytes[nextcluster*4:nextcluster*4+4]
                nextcluster = struct.unpack("<i", chunk)[0]
                if (debug >= 3):
                        print ('\tCluster Read [Length]: ' + '[' + str(len(chunk)) + ']' + str(chunk))
                if (debug >= 2):
                    print ('\tNext Cluster: ' + str(nextcluster))
                if (nextcluster != -8):
                    readclusterlist.append(nextcluster)
                else:
                    break
        if (debug >= 2):
                    print('\tCluster List: ' + str(readclusterlist))
        return readclusterlist
    except:
        sys.exit('Error: Cannot read Search FAT.')


def ReadData(volume, clusterlist, size):
        try:
            if (debug >= 1):
                print('Entering ReadData:')
            if (debug >= 2):
                print('Volume Passed in: ' + str(volume))
                print('Clusterlist Passed in: ' + str(clusterlist))
                print('Size in: ' + str(size))
            readchunk = bytearray()
            with open(volume, "rb") as f:
                for cluster in clusterlist:  #New Offset is 2 (Cluster)
                    seeker = (cluster * ClusterSize + (DataAreaStart * 512) - 2 * ClusterSize)
                    f.seek(seeker)  #Each ClusterNum - 2 (Offset) * Bytes per cluster + (DataAreaStart * 512)
                    if (debug >= 2):
                        print('\tSeeking to Cluster (Bytes) [Cluster]: ' + '[' + str(cluster) + ']' + str(seeker))
                    readchunk += f.read(ClusterSize)
                filedata = readchunk[0:size]
                if (debug >= 3):
                        print ('\tFile Data: ' + str(filedata))
                return filedata
        except:
            sys.exit('Error: Cannot Read Data.')


def WriteDatatoFile(file, filedata):
        try:
            if (debug >= 1):
                print('Entering WriteDatatoFile:')
            with open(file, "wb") as f:
                f.write(filedata)
            md5 = hashlib.md5()
            md5.update(filedata)
            return md5.hexdigest()
        except:
            sys.exit('Error: Cannot Write Data.')


def WriteFSInfo(volume):
    #try:
        if (debug >= 1):
            print('Entering WriteFSInfo:')
        #Number of Free Clusters - 488-491
        #Next Free Cluster 492-495
        global NumberOfFreeClusters
        global NextFreeCluster

        with open(volume, "rb+") as f:
            f.seek(FSInfoSector * 512 + 488)
            f.write(struct.pack("i", NumberOfFreeClusters))
            if (debug >= 2):
                print ('Number of Free Clusters: ' + str(NumberOfFreeClusters))
            f.seek(FSInfoSector * 512 + 492)
            f.write(struct.pack("i", NextFreeCluster))
            if (debug >= 2):
                print ('Next Free Cluster: ' + str(NextFreeCluster))
    #except:


def FlagValues(mask):
    if (debug >= 2):
        print('Entering FlagValues:')
    if (mask == 0x10):
        return 'directory'
    elif (mask == 0x08):
        return 'volume'
    else:
        return 'file'


def signal_handler(signal, frame):
    print('Ctrl+C pressed. Exiting.')
    sys.exit(0)


def usage():
    print('A FAT32 file system writer that forces fragmentation.')
    print('Usage: frag.py -fnvdr|h')
    print('')
    print('Required arguments:')
    print('-f, --file\t\tThe file to write to the FAT32 volume.')
    print('-v, --volume\t\tThe volume to write the fragmented file to.')
    print('Optional arguments:')
    print('-n, --number\t\tThe number of fragments to create.')
    print('-r, --read\t\tThe file to read from FAT32 volume.')
    print('-d, --debug\t\tThe level of debugging.')
    print('-h, --help\t\tThis help output.')


signal.signal(signal.SIGINT, signal_handler)


def main(argv):
    try:
        global debug
        global MD5HashValue
        #parse the command-line arguments
        fragments = int(0)
        write = False
        parser = argparse.ArgumentParser(description="A FAT32 file system writer that forces fragmentation.",
                                         add_help=True)
        parser.add_argument('-f', '--file', help='The filename to read/write to the FAT32 volume.', required=True)
        parser.add_argument('-n', '--number', help='The number of fragments to create.', type=int, required=False)
        parser.add_argument('-v', '--volume', help='The volume to write the fragmented file to.', required=True)
        parser.add_argument('-d', '--debug', help='The level of debugging.', required=False)
        rwgroup = parser.add_mutually_exclusive_group()
        rwgroup.add_argument('-w', '--write', help='The file to write to the FAT32 volume.', action='store_true', required=False)
        rwgroup.add_argument('-r', '--read', help='The file to read from FAT32 volume.', action='store_true', required=False)
        parser.add_argument('--version', action='version', version='%(prog)s 1.0')
        args = parser.parse_args()
        if (args.read):
            read = args.read
        else:
            read = False
        if (args.file):
            file = args.file
            if not (read):
                with open(file):
                    check = True
                MD5HashValue = HashMD5(file)
        if (args.volume):
            volume = args.volume
        if (args.number):
            fragments = args.number
            fragments = int(fragments)
        if (args.volume):
            volume = args.volume

        if (args.debug):
            debug = args.debug
            debug = int(debug)
        if _platform == "linux" or _platform == "linux2":
            os = 'Linux'
        elif _platform == "darwin":
            os = 'Mac'
        elif _platform == "win32":
            os = 'Windows'
        if (debug >= 1):
            print('Entered main:')
            print('\tFilename to Fragment: ' + str(file))
            print('File Input: ' + str(ntpath.basename(file)) + ' - ' + 'MD5: ' + str(MD5HashValue))
            print('\tNumber of Fragments: ' + str(fragments))
            print('\tVolume: ' + str(volume))
            print('\tOperating System: ' + str(os))
            print('\tDebug Level: ' + str(debug))
        #if (os == 'Windows'):
        #    print ('Error: System not supported.')
        #    sys.exit(1)

        ReadBootSector(volume)

        if not (read):
            if (MinFileLength(file, fragments)):
                print('')
                print('+------------------------------------------------------------------------+')
                print('|FAT32 File Fragmentation Utility                                        |')
                print('+-------------------------------------------------------------------------')
                print('|Author: Tahir Khan - tkhan9@gmu.edu                                     |')
                print('+------------------------------------------------------------------------+')
                print('  Date Run: ' + str(datetime.datetime.now()))
                print('  File: ' + str(ntpath.basename(file)) + ' - ' + 'MD5: ' + str(MD5HashValue))
                print('+------------------------------------------------------------------------+')
                print('| Reading Data.                                                          |')
                GetChunks(file)
                print('| Reading FAT.                                                           |')
                ReadFat(volume, ReservedSectorCount, TotalChunks, fragments)
                print('| Reading Directory.                                                     |')
                ReadDirectory(volume, file)
                print('| Writing Directory.                                                     |')
                WriteDirectory(file, volume, FreeDirOffset, FirstCluster)
                print('| Writing FAT.                                                           |')
                WriteFAT(volume, ReservedSectorCount, ChunkList)
                print('| Writing Data.                                                          |')
                WriteData(volume, file, ChunkList)
                print('| Getting Next Free Cluster.                                             |')
                GetNextFreeCluster(volume)
                print('| Writing FSInfo.                                                        |')
                WriteFSInfo(volume)
                print('| Completed.                                                             |')
                print('+------------------------------------------------------------------------+')
            else:
                print('Error: Filesize too Small.')
                sys.exit(1)
        else:
            print('')
            print('+------------------------------------------------------------------------+')
            print('|FAT32 File Fragmentation Utility                                        |')
            print('+-------------------------------------------------------------------------')
            print('|Author: Tahir Khan - tkhan9@gmu.edu                                     |')
            print('+------------------------------------------------------------------------+')
            print('  Date Run: ' + str(datetime.datetime.now()))
            print('+------------------------------------------------------------------------+')
            print('| Searching Directory                                                    |')
            SearchDirectory(volume, ntpath.basename(file), write)
            print('| Searching FAT                                                          |')
            clusterlist = SearchFAT(volume, ReservedSectorCount, FirstCluster)
            print('| Reading Data                                                           |')
            filedata = ReadData(volume, clusterlist, FileSize)
            print('| Writing Data                                                           |')
            print('| Completed.                                                             |')
            print('+------------------------------------------------------------------------+')
            print('+------------------------------------------------------------------------+')
            print('  File: ' + str(ntpath.basename(file)) + ' - ' + 'MD5: ' + str(WriteDatatoFile(file, filedata)))
            print('+------------------------------------------------------------------------+')



    except IOError:
        sys.exit('Error: File ' + str(file) + ' does not exist.')


main(sys.argv[1:])