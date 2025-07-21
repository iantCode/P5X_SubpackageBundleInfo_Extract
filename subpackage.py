from typing import BinaryIO

def add_pad(length):
    return length + 4 - length % 4


def get_bundle_folder_num(filename: str) -> int:
    hash_val = 0
    mul_value = 131

    for char in filename:
        hash_val = (hash_val * mul_value + ord(char)) & 0xFFFFFFFF
    
    if hash_val & 0x80000000:
        hash_val -= 0x100000000
    
    hash_val = (hash_val & 0x7FFFFFFF)

    return hash_val % 200


class FlatBuf:
    _table = {}

    def table(self, file: BinaryIO, offset: int) -> None:
        file.seek(offset)
        table_offset = file.tell() - int.from_bytes(file.read(4), "little", signed=True)
        file.seek(table_offset)
        entry_count = int.from_bytes(file.read(2), "little") // 2 - 2
        table_size = int.from_bytes(file.read(2), "little") # unused

        for i in range(entry_count):
            value = int.from_bytes(file.read(2), "little")
            self._table[i] = value


class SubpackageHeader(FlatBuf):
    next_offset: int = int()
    map_header_offset: int = int()
    chunklist_offset: int = int()
    bundlechunk_names: list[str]
    bundlechunk_offsets: list[int]
    chunklist_name: str = str()
    is_small: bool = False

    @classmethod
    def read(cls, file: BinaryIO) -> 'SubpackageHeader':
        
        header = cls()
        start_entry = int.from_bytes(file.read(4), "little")

        header.table(file, start_entry)

        file.seek(start_entry + header._table[0])
        header.next_offset = file.tell() + int.from_bytes(file.read(4), "little")
        file.seek(start_entry + header._table[1])
        header.map_header_offset = file.tell() + int.from_bytes(file.read(4), "little")

        if 3 in header._table:
            header.is_small = False
            file.seek(start_entry + header._table[2])
            header.chunklist_offset = file.tell() + int.from_bytes(file.read(4), "little")
            file.seek(start_entry + header._table[3])
            bundlechunk_count_offset = file.tell() + int.from_bytes(file.read(4), "little")
            file.seek(bundlechunk_count_offset)
            bundlechunk_count = int.from_bytes(file.read(4), "little")
            header.bundlechunk_offsets = []
            for _ in range(bundlechunk_count):
                header.bundlechunk_offsets.append(file.tell() + int.from_bytes(file.read(4), "little"))

        else:
            header.is_small = True
            file.seek(start_entry + header._table[2])
            file.read(4)
            bundlechunk_count = int.from_bytes(file.read(4), "little")
            for _ in range(bundlechunk_count):
                header.bundlechunk_offsets.append(file.tell() + int.from_bytes(file.read(4), "little"))

        header.bundlechunk_names = []
        for _ in range(bundlechunk_count):
            length = int.from_bytes(file.read(4), "little")
            bundlename = file.read(add_pad(length)).decode('ascii').split('\x00', 1)[0]
            header.bundlechunk_names.append(bundlename)

        if 3 in header._table:
            length = int.from_bytes(file.read(4), "little")
            header.chunklist_name = file.read(add_pad(length)).decode('ascii').split('\x00', 1)[0]
        else:
            header.chunklist_name = ""

        return header
    

class FileMapHeader:
    file_count: int = int()
    file_offsets: list[int]

    @classmethod
    def read(cls, file: BinaryIO, offset: int) -> 'FileMapHeader':
        filemap = cls()
        file.seek(offset)
        filemap.file_count = int.from_bytes(file.read(4), "little")
        filemap.file_offsets = [file.tell() + int.from_bytes(file.read(4), "little") for _ in range(filemap.file_count)]

        return filemap
    

class SmallFileMap:
    file_count: int = int()
    name: str = str()
    files: list['FileEntry']
    file_index_list: list[int]

    @classmethod
    def read(cls, file: BinaryIO, offset: int) -> 'SmallFileMap':
        small_map = cls()
        file.seek(offset)
        length = int.from_bytes(file.read(4), "little")
        small_map.name = file.read(add_pad(length)).decode('ascii').split('\x00', 1)[0]

        small_map.file_count = int.from_bytes(file.read(4), "little")
        return small_map

class FileMap(FlatBuf):
    file_count: int = int()
    file_index_list: list[int]
    name: str = str()
    files: list['FileEntry']

    @classmethod
    def read(cls, file: BinaryIO, offset: int) -> 'FileMap':
        file_map = cls()
        file.seek(offset)
        
        file_map.table(file, offset)
        
        file.seek(offset + file_map._table[0])
        name_offset = file.tell() + int.from_bytes(file.read(4), "little")
        file.seek(offset + file_map._table[1])
        count_offset = file.tell() + int.from_bytes(file.read(4), "little")
        file.seek(name_offset)
        length = int.from_bytes(file.read(4), "little")
        file_map.name = file.read(add_pad(length)).decode('ascii').split('\x00', 1)[0]

        file.seek(count_offset)
        file_map.file_count = int.from_bytes(file.read(4), "little")

        file_map.file_index_list = []
        for _ in range(file_map.file_count):
            file_map.file_index_list.append(int.from_bytes(file.read(4), "little"))
        file_map.files = []

        return file_map
    

class FileEntry(FlatBuf):
    filename: str = str()
    crc32: int = int()
    filesize: int = int()
    bundlechunk_index: int = int()
    file_offset: int = int()
    bundle_folder_index: str = str()
    bundlechunk_name: str = str()
    is_bundle: bool = False

    @classmethod
    def read(cls, file: BinaryIO, offset: int) -> 'FileEntry':
        file_entry = cls()
        file.seek(offset)
        file_entry.table(file, offset)

        file.seek(offset + file_entry._table[0])
        name_offset = file.tell() + int.from_bytes(file.read(4), "little")
        file.seek(name_offset)
        length = int.from_bytes(file.read(4), "little")
        file_entry.filename = file.read(add_pad(length)).decode('ascii').split('\x00', 1)[0]

        file.seek(offset + file_entry._table[1])
        file_entry.crc32 = int.from_bytes(file.read(4), "little")

        file.seek(offset + file_entry._table[2])
        file_entry.filesize = int.from_bytes(file.read(4), "little")

        if 3 not in file_entry._table or file_entry._table[3] == 0:
            file_entry.bundlechunk_index = 0
        else:
            file.seek(offset + file_entry._table[3])
            file_entry.bundlechunk_index = int.from_bytes(file.read(4), "little")

        if 4 in file_entry._table:
            if file_entry._table[4] == 0:
                file_entry.file_offset = 0
            else:
                file.seek(offset + file_entry._table[4])
                file_entry.file_offset = int.from_bytes(file.read(4), "little")
        else:
            file_entry.file_offset = 0

        file_entry.is_bundle = False
        if 5 in file_entry._table:
            if file_entry._table[5] == 0:
                file_entry.is_bundle = False
            else:
                file.seek(offset + file_entry._table[5])
                file_entry.is_bundle = True
                file_entry.bundle_folder_index = get_bundle_folder_num(file_entry.filename)

        return file_entry
    

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "crc32": hex(self.crc32),
            "bundlechunk_name": self.bundlechunk_name,
            "filesize": self.filesize,
            "file_offset": self.file_offset,
            "is_bundle": self.is_bundle,
            "bundle_folder_index": self.bundle_folder_index,
        }


class Subpackage():
    header: 'SubpackageHeader' = None
    all_maps: list['FileMap']

    @classmethod
    def read(cls, filename: str) -> 'Subpackage':
        """
            Read a subpackage file and return a Subpackage object.
            Args:
                filename (str): The name of the subpackage file to read.
            Returns:
                Subpackage: An instance of the Subpackage class containing the parsed data.
        """
        subpackage = cls()
        file = open(filename, "rb")
        subpackage.header = SubpackageHeader.read(file)

        subpackage.all_maps = []
        if not subpackage.header.is_small:
            file_map_header = FileMapHeader.read(file, subpackage.header.map_header_offset)
            for ptr in file_map_header.file_offsets:
                file_map = FileMap.read(file, ptr)
                subpackage.all_maps.append(file_map)
        else:
            map_headers = SmallFileMap.read(file, file.tell())
            subpackage.all_maps.append(map_headers)

        file.seek(subpackage.header.next_offset)
        file.read(4)

        file_offset_list = []
        for map in subpackage.all_maps:
            for _ in range(map.file_count):
                file_offset = file.tell() + int.from_bytes(file.read(4), "little")
                file_offset_list.append(file_offset)
        file_offset_list.reverse()

        for idx, file_offset in enumerate(file_offset_list):
            file_entry = FileEntry.read(file, file_offset)
            file_entry.bundlechunk_name = subpackage.header.bundlechunk_names[file_entry.bundlechunk_index]

            if len(subpackage.all_maps) == 1:
                subpackage.all_maps[0].files.append(file_entry)
            else:
                for map in subpackage.all_maps:
                    if idx in map.file_index_list:
                        map.files.append(file_entry)
                        break

        file.close()
        return subpackage

    def to_json(self, filename: str) -> None:
        """
            Convert the subpackage data to JSON format and save it to a file.
            args:
                filename (str): The name of the file to save the JSON data.
        """
        import json
        data = {
            "header": {
                "bundlechunk_names": self.header.bundlechunk_names,
                "chunklist_name": self.header.chunklist_name
            },
            "map_headers": []
        }

        for map in subpackage.all_maps:
            data["map_headers"].append({
                "name": map.name,
                "file_count": map.file_count,
                "real_file_count": len(map.files),
                "files": [file.to_dict() for file in map.files]
            })

        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)


if __name__ == "__main__":
    filename = "SubpackageBundleInfo.txt"
    subpackage = Subpackage.read(filename)
    subpackage.to_json("SubpackageBundleInfo.json")