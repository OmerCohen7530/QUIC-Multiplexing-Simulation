import unittest
from unittest.mock import patch, MagicMock
import socket
import time
from StreamIn import StreamIn
import QUIC_API

def create_packet(packet_num, data=''):
    """Utility function to create a packet for testing."""
    return QUIC_API.create_packet(packet_num, data)

class TestStreamIn(unittest.TestCase):
    def setUp(self):
        # Initialize StreamIn instance with mocked parameters
        self.stream_in = StreamIn('127.0.0.1', 9000, 1, time.time(), lambda *args: None)
        self.stream_in.socket.close()

    def tearDown(self):
        # Ensure the socket is closed after each test
        if self.stream_in.socket:
            self.stream_in.socket.close()
        if self.stream_in.log_file and not self.stream_in.log_file.closed:
            self.stream_in.log_file.close()

    @patch('socket.socket')
    def test_initialize_connection(self, mock_socket):
        """Test initialization and connection setup."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket

        # Simulate receiving the stream size
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(0, '1024'), ('127.0.0.1', 5000)),  # Simulate receiving stream size
        ]

        # Run the method to test
        self.stream_in.initialize_connection()

        # Check if the data size is set correctly
        self.assertEqual(self.stream_in.data_size, 1032)  # 1024 + header size

        # Ensure the SYN was sent and ACK received
        self.assertEqual(mock_stream_socket.sendto.call_count, 2)
        mock_stream_socket.recvfrom.assert_called_once()

    @patch('socket.socket')
    def test_receive_data_and_ack(self, mock_socket):
        """Test receiving data and sending ACKs."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        # Simulate receiving data and EOF
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(1, 'data_chunk'), ('127.0.0.1', 5000)),  # Simulate receiving a data chunk
            (create_packet(2, 'EOF'), ('127.0.0.1', 5000)),  # Simulate receiving EOF
        ]

        # Mock the log method to prevent actual file I/O during logging
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            # Run the method that processes receiving data
            self.stream_in.receive_data()

            # Ensure data and EOF were logged
            mock_log.assert_any_call(f"Received packet #1 with 10 bytes and sent ACK")
            mock_log.assert_any_call("Received EOF from server.")  # Updated expected log message

    @patch('socket.socket')
    def test_idle_connection_handling(self, mock_socket):
        """Test handling when no data is received for a period of time (idle connection)."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        # Simulate receiving a data packet, then no data for a period (idle)
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(1, 'data_chunk'), ('127.0.0.1', 5000)),  # Simulate receiving a data chunk
            socket.timeout,  # Simulate no data received (timeout) - idle period
            socket.timeout,  # Simulate no data received (timeout) - idle period
        ]

        # Mock the log method to prevent actual file I/O during logging
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            # Run the method that processes receiving data
            self.stream_in.receive_data()

            # Ensure data received and idle connection are logged
            mock_log.assert_any_call(f"Received packet #1 with 10 bytes and sent ACK")
            mock_log.assert_any_call("Timeout occurred while waiting for data.")  # Log idle period
            mock_log.assert_any_call("Timeout occurred while waiting for data.")  # Log idle period again

    @patch('socket.socket')
    def test_receive_multiple_packets(self, mock_socket):
        """Test data reception with multiple packets."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        # Simulate receiving multiple packets
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(1, 'data1'), ('127.0.0.1', 5000)),
            (create_packet(2, 'data2'), ('127.0.0.1', 5000)),
            (create_packet(3, 'EOF'), ('127.0.0.1', 5000)),
        ]

        # Mock the log method
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            self.stream_in.receive_data()

            # Check logs for multiple packets
            mock_log.assert_any_call(f"Received packet #1 with 5 bytes and sent ACK")
            mock_log.assert_any_call(f"Received packet #2 with 5 bytes and sent ACK")
            mock_log.assert_any_call("Received EOF from server.")

    @patch('socket.socket')
    def test_invalid_packet_handling(self, mock_socket):
        """Test handling of invalid or malformed packets."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        # Simulate receiving a malformed packet
        mock_stream_socket.recvfrom.side_effect = [
            (b'invalid_packet', ('127.0.0.1', 5000)),  # Invalid data
        ]

        # Mock the log method
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            self.stream_in.receive_data()

            # Ensure the invalid packet is logged as an error
            mock_log.assert_any_call("Error while receiving data: invalid literal for int() with base 10: 'invalid_'")

    @patch('socket.socket')
    def test_large_data_reception(self, mock_socket):
        """Test handling of large data reception."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        large_data = 'X' * 1024  # Simulate large data packet
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(1, large_data), ('127.0.0.1', 5000)),
            (create_packet(2, 'EOF'), ('127.0.0.1', 5000)),
        ]

        # Mock the log method
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            self.stream_in.receive_data()

            # Check log for large data
            mock_log.assert_any_call(f"Received packet #1 with 1024 bytes and sent ACK")
            mock_log.assert_any_call("Received EOF from server.")

    @patch('socket.socket')
    def test_error_logging(self, mock_socket):
        """Test logging of errors during data reception."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        # Simulate a runtime error
        mock_stream_socket.recvfrom.side_effect = RuntimeError("Simulated error")

        # Mock the log method
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            self.stream_in.receive_data()

            # Ensure error is logged
            mock_log.assert_any_call("Error while receiving data: Simulated error")  # Updated expected log message

    @patch('socket.socket')
    def test_ack_resending_on_timeout(self, mock_socket):
        """Test proper ACK resending on timeout."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        # Simulate ACK timeout and then successful ACK
        mock_stream_socket.recvfrom.side_effect = [
            socket.timeout,  # Timeout on first try
            (create_packet(1, 'ACK'), ('127.0.0.1', 5000)),  # Successful ACK
        ]

        # Mock the log method
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            self.stream_in.receive_data()

            # Check if timeout and retry were logged
            mock_log.assert_any_call("Timeout occurred while waiting for data.")
            mock_log.assert_any_call(f"Sent ACK for packet #1")

    @patch('socket.socket')
    def test_connection_closure_behavior(self, mock_socket):
        """Test proper behavior when the connection is closed."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_in.socket = mock_stream_socket
        self.stream_in.client_address = ('127.0.0.1', 5000)

        # Simulate the connection being closed unexpectedly
        mock_stream_socket.recvfrom.side_effect = OSError("Connection closed")

        # Mock the log method
        with patch.object(self.stream_in, 'log', wraps=self.stream_in.log) as mock_log:
            self.stream_in.receive_data()

            # Ensure the connection closure is logged
            mock_log.assert_any_call("Error while receiving data: Connection closed")  # Updated expected log message


if __name__ == '__main__':
    unittest.main()
