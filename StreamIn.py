import socket
import time
import os
import QUIC_API

class StreamIn:
    """
    A class representing a stream receiver that connects to a QUIC server to receive data in chunks.

    Attributes:
        server_host (str): The server's IP address.
        server_port (int): The server's port number.
        index (int): Index of the stream.
        socket (socket.socket): The UDP socket for the stream.
        data_size (int): Size of the data to be received.
        global_start_time (float): The start time for the data transfer session.
        add_stream_data (function): Callback function to add received data statistics to the client.
        total_data_received (int): Total number of bytes received.
        total_packets_received (int): Total number of packets received.
        log_file (file object): The file object used for logging stream events.
    """

    def __init__(self, server_host, server_port, index, global_start_time, add_stream_data_callback):
        """
        Initializes the stream receiver with server details and logging configuration.

        Parameters:
            server_host (str): The server's IP address.
            server_port (int): The server's port number.
            index (int): The index of this stream.
            global_start_time (float): The start time of the data transfer session.
            add_stream_data_callback (function): Callback to update the client with received data statistics.
        """
        self.server_host = server_host
        self.server_port = server_port
        self.index = index
        self.socket = self.create_socket()
        self.data_size = None
        self.global_start_time = global_start_time
        self.add_stream_data = add_stream_data_callback
        self.total_data_received = 0  # Track total bytes received
        self.total_packets_received = 0  # Track total packets received

        # Create the output directory if it doesn't exist
        os.makedirs('out', exist_ok=True)
        self.log_file = open(f'out/streams_in_{self.index}.txt', 'w')  # Open log file for writing

    def create_socket(self):
        """
        Creates and configures a UDP socket for the stream.

        Returns:
            socket.socket: A configured UDP socket for data reception.
        """
        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return stream_socket

    def log(self, message):
        """
        Logs a message to the stream's log file.

        Parameters:
            message (str): The message to log.
        """
        self.log_file.write(f"Stream {self.index}: {message}\n")

    def close_resources(self):
        """
        Closes the socket and the log file.
        """
        self.socket.close()
        self.log_file.close()

    def initialize_connection(self):
        """
        Initializes the connection by sending a SYN message and receiving the stream size.
        """
        self.log(f"Connecting to {self.server_host}:{self.server_port}")
        self.send_syn()
        self.receive_stream_size()

    def send_syn(self):
        """
        Sends a SYN message to the server to start the connection.
        """
        syn_message = QUIC_API.create_packet(0, "Syn")
        self.socket.sendto(syn_message, (self.server_host, self.server_port))
        self.log(f"Sent SYN to {self.server_host}:{self.server_port}")

    def receive_stream_size(self):
        """
        Receives the stream size from the server and sends an ACK.
        """
        packet, _ = self.socket.recvfrom(1024)
        packet_num, data = QUIC_API.parse_packet(packet)
        self.data_size = int(data) + 8  # Include header size
        self.log(f"Data size is {self.data_size} bytes")
        self.send_ack(packet_num)

    def send_ack(self, packet_num):
        """
        Sends an ACK packet for the received data.

        Parameters:
            packet_num (int): The packet number to acknowledge.
        """
        ack_packet = QUIC_API.create_packet(packet_num)
        self.socket.sendto(ack_packet, (self.server_host, self.server_port))
        self.log(f"Sent ACK for packet #{packet_num}")

    def receive_data(self):
        """
        Receives data from the server in chunks and sends ACKs for each chunk.
        """
        while True:
            try:
                packet, _ = self.socket.recvfrom(self.data_size)
                packet_num, data = QUIC_API.parse_packet(packet)

                if data == 'EOF':
                    self.log("Received EOF from server.")
                    break  # End of data transmission

                self.handle_received_data(packet_num, data)

            except socket.timeout:
                self.log("Timeout occurred while waiting for data.")  # Log the timeout event
                continue  # Continue listening for data
            except Exception as e:
                self.log(f"Error while receiving data: {e}")
                break  # Break the loop if another error occurs

    def handle_received_data(self, packet_num, data):
        """
        Handles the received data, logs it, and sends an ACK.

        Parameters:
            packet_num (int): The number of the received packet.
            data (bytes): The data received in the packet.
        """
        # Calculate the time elapsed
        time_elapsed = time.time() - self.global_start_time

        # Record the data received and packets to the QuicClient
        self.total_data_received += len(data)
        self.total_packets_received += 1

        # Call with exactly 3 arguments (time_elapsed, data_received, packets_received)
        self.add_stream_data(time_elapsed, len(data), 1)

        # Send an ACK with the packet number back to the server
        self.send_ack(packet_num)
        self.log(f"Received packet #{packet_num} with {len(data)} bytes and sent ACK")

    def get_stats(self):
        """
        Returns the statistics for this stream.

        Returns:
            dict: A dictionary containing total time, stream index, total data received, total packets received,
                  data size, bytes per second, and packets per second.
        """
        elapsed_time = time.time() - self.global_start_time
        bytes_per_second = self.total_data_received / elapsed_time if elapsed_time > 0 else 0
        packets_per_second = self.total_packets_received / elapsed_time if elapsed_time > 0 else 0
        return {
            'total_time': elapsed_time,
            'stream_index': self.index,
            'total_data_received': self.total_data_received,
            'total_packets_received': self.total_packets_received,
            'data_size': self.data_size,
            'bytes_per_second': bytes_per_second,
            'packets_per_second': packets_per_second
        }

    def start(self):
        """
        Main entry point to start receiving data from the server.
        """
        try:
            self.initialize_connection()
            self.receive_data()
            self.log("Completed receiving data.")
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.close_resources()
