import unittest
from unittest.mock import patch, MagicMock
import socket
from QuicServer import QuicServer
import QUIC_API

class TestQuicServer(unittest.TestCase):

    @patch('socket.socket')
    @patch('threading.Thread')
    def test_server_initialization_and_socket_setup(self, mock_thread, mock_socket):
        """Test server initialization and socket setup."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Initialize the server with mock socket and thread
        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        server.server_socket.close()

        # Ensure the server socket is created and bound
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_server_socket.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_server_socket.bind.assert_called_once_with(('127.0.0.1', 8000))

        # Check that data files are created without actual I/O
        self.assertEqual(len(server.sizes), 4)  # Should have 4 streams
        print("Test server initialization passed.")




    @patch('socket.socket')
    @patch('QUIC_API.parse_packet')
    def test_wait_for_client_syn(self, mock_parse_packet, mock_socket):
        """Test waiting for client SYN message."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        # Mock receiving a SYN packet from the client
        mock_server_socket.recvfrom.return_value = (b'00000000 Syn', ('127.0.0.1', 12345))

        # Mock the parse_packet method to return expected values
        mock_parse_packet.return_value = (0, "Syn")

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        server.wait_for_client_syn()

        # Ensure the client address is correctly assigned
        self.assertEqual(server.client_address, ('127.0.0.1', 12345))
        print("Test wait for client SYN passed.")

    @patch('socket.socket')
    def test_send_number_of_streams(self, mock_socket):
        """Test sending the number of streams to the client."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        server.client_address = ('127.0.0.1', 12345)  # Set client address directly

        # Call the method to send the number of streams
        server.send_number_of_streams()

        # Ensure the packet was sent with the correct number of streams
        mock_server_socket.sendto.assert_called_once()
        print("Test send number of streams passed.")

    @patch('socket.socket')
    def test_wait_for_ack(self, mock_socket):
        """Test waiting for ACK from the client."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        # Mock receiving an ACK
        mock_server_socket.recvfrom.return_value = (b'00000001 ACK', ('127.0.0.1', 12345))

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        ack_received = server.wait_for_ack(1)

        # Ensure ACK was received
        self.assertTrue(ack_received)
        print("Test wait for ACK passed.")

    @patch('socket.socket')
    @patch('threading.Thread')
    def test_start_stream_threads(self, mock_thread, mock_socket):
        """Test starting stream threads for data transmission."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        server.client_address = ('127.0.0.1', 12345)  # Set client address directly

        # Mock the methods called within start_stream_threads
        server.send_stream_port_to_client = MagicMock()
        server.wait_for_ack = MagicMock(return_value=True)

        # Call the method to start stream threads
        server.start_stream_threads()

        # Ensure that threads were started
        self.assertEqual(mock_thread.call_count, 4)
        print("Test start stream threads passed.")

    @patch('socket.socket')
    @patch('QUIC_API.parse_packet')
    def test_invalid_syn_message(self, mock_parse_packet, mock_socket):
        """Test handling of invalid SYN message."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        # Mock receiving an invalid SYN packet from the client
        mock_server_socket.recvfrom.return_value = (b'00000000 Invalid', ('127.0.0.1', 12345))
        mock_parse_packet.return_value = (0, "Invalid")

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)

        # Test for ValueError when an invalid SYN message is received
        with self.assertRaises(ValueError):
            server.wait_for_client_syn()

    @patch('socket.socket')
    @patch('QUIC_API.parse_packet')
    def test_timeout_waiting_for_ack(self, mock_parse_packet, mock_socket):
        """Test handling of timeout while waiting for ACK."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        # Simulate a timeout during ACK reception
        mock_server_socket.recvfrom.side_effect = socket.timeout

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        server.server_socket.settimeout(1)  # Set a short timeout for the test

        # Test that the wait_for_ack method returns False on timeout
        result = server.wait_for_ack(0)
        self.assertFalse(result)

    @patch('socket.socket')
    @patch('QUIC_API.create_packet')
    def test_send_stream_port_to_client(self, mock_create_packet, mock_socket):
        """Test sending stream port to client."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        server.client_address = ('127.0.0.1', 12345)  # Set client address directly

        # Mock packet creation
        mock_create_packet.return_value = b'packet_data'

        # Simulate sending stream port
        server.send_stream_port_to_client(0, 8001)

        # Assert that sendto was called with the correct packet and address
        mock_server_socket.sendto.assert_called_with(b'packet_data', server.client_address)

    @patch('socket.socket')
    @patch('threading.Thread')
    @patch('StreamOut.StreamOut')
    def test_wait_for_all_threads(self, mock_stream_out, mock_thread, mock_socket):
        """Test waiting for all threads to complete."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        mock_stream_instance = MagicMock()
        mock_stream_out.return_value = mock_stream_instance

        # Mock separate thread instances for each call
        mock_thread.side_effect = [MagicMock() for _ in range(4)]

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)
        server.client_address = ('127.0.0.1', 12345)  # Set client address directly

        # Mock `recvfrom` to return an ACK message for each expected packet number
        mock_server_socket.recvfrom.side_effect = [(b'00000001 ACK', server.client_address),
                                                   (b'00000002 ACK', server.client_address),
                                                   (b'00000003 ACK', server.client_address),
                                                   (b'00000004 ACK', server.client_address)]

        # Start stream threads
        server.start_stream_threads()

        # Call the method under test
        server.wait_for_all_threads()

        # Assert that each thread's join method was called once
        for thread in mock_thread.side_effect:
            thread.join.assert_called_once()

    @patch('socket.socket')
    @patch('threading.Thread')
    @patch('StreamOut.StreamOut')
    def test_server_start(self, mock_stream_out, mock_thread, mock_socket):
        """Test the entire server start process."""
        mock_server_socket = MagicMock()
        mock_socket.return_value = mock_server_socket

        mock_stream_instance = MagicMock()
        mock_stream_out.return_value = mock_stream_instance

        # Mock separate thread instances for each call
        mock_thread.side_effect = [MagicMock() for _ in range(4)]

        server = QuicServer('127.0.0.1', 8000, 4, total_size=0.1, ack_timeout=5, is_test=True)

        # Mock client address
        client_address = ('127.0.0.1', 12345)

        # Mock `recvfrom` to simulate SYN, ACKs, and EOF signals
        mock_server_socket.recvfrom.side_effect = [
            (QUIC_API.create_packet(0, 'Syn'), client_address),  # SYN from client
            (QUIC_API.create_packet(0, ''), client_address),  # ACK for number of streams
            (QUIC_API.create_packet(1, ''), client_address),  # ACK for stream 1
            (QUIC_API.create_packet(2, ''), client_address),  # ACK for stream 2
            (QUIC_API.create_packet(3, ''), client_address),  # ACK for stream 3
            (QUIC_API.create_packet(4, ''), client_address)  # ACK for stream 4
        ]

        # Run the server start process
        server.start()

        # Ensure all expected interactions occurred
        mock_server_socket.recvfrom.assert_called()  # Ensure server waits for client SYN

        # Ensure number of streams sent matches expected
        number_of_streams_packet = QUIC_API.create_packet(0, str(server.streams))
        mock_server_socket.sendto.assert_any_call(number_of_streams_packet, client_address)

        # Assert that the correct number of threads were started
        self.assertEqual(mock_thread.call_count, 4)

        # Ensure each thread was started
        for thread in server.threads:
            thread.start.assert_called_once()

        # Ensure all threads were joined
        for thread in mock_thread.side_effect:
            thread.join.assert_called_once()


if __name__ == '__main__':
    unittest.main()
