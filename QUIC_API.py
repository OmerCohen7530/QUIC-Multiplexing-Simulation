import random
import string

def create_data(size_in_bytes):
    """
    Generates random data of a specified size in bytes using alphabetic characters.

    Parameters:
        size_in_bytes (int): The size of the data to generate in bytes.

    Returns:
        str: A string of randomly generated alphabetic characters of the specified size.
    """
    chars = string.ascii_letters
    return ''.join(random.choice(chars) for _ in range(size_in_bytes))

def parse_packet(packet):
    """
    Extracts the packet number and data from a given packet.

    Parameters:
        packet (bytes): The packet containing both the packet number (header) and data.

    Returns:
        tuple: A tuple (packet_number, data) where packet_number is an integer and data is the actual payload
               (decoded string if possible, otherwise bytes).
    """
    header_size = 8  # Size for the packet number header

    # Extract the packet number using decode and strip
    packet_number = int(packet[:header_size].decode().strip())

    # Extract the data part by skipping the header
    data = packet[header_size:]

    try:
        # Attempt to decode the data (assuming it's text data)
        return packet_number, data.decode('utf-8')
    except UnicodeDecodeError:
        # If it's binary data that can't be decoded, return the raw bytes
        return packet_number, data

def create_file(data, index):
    """
    Creates a text file with the provided data.

    Parameters:
        data (str): The content to write to the file.
        index (int): The index used in the filename to distinguish it.
    """
    with open("out/file_" + str(index) + ".txt", 'w') as file:
        file.write(data)


def create_packet(packet_id, data=''):
    """
    Creates a packet with a specified packet ID and optional data.

    Parameters:
        packet_id (int): The unique identifier for the packet.
        data (str): The payload data to be included in the packet (optional, defaults to an empty string).

    Returns:
        bytes: The encoded packet, including the packet ID as a header and the data as the payload.
    """
    packet_id_encoded = str(packet_id).zfill(8).encode()
    data_str = str(data)
    data_encoded = data_str.encode()
    return packet_id_encoded + data_encoded
