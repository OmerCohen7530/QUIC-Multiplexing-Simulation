
# QUIC - Multiplexing

## Overview
This project demonstrates the implementation of the QUIC protocol with a focus on multiplexing multiple streams over a single connection. It highlights the benefits of QUIC, such as reduced head-of-line blocking, improved congestion control, and better performance compared to TCP.

## Files and Structure
- QuicClient.py: QUIC client implementation.
- QuicServer.py: QUIC server implementation.
- QUIC_API.py: Utility functions for the QUIC protocol.
- StreamIn.py / StreamOut.py: Handle incoming and outgoing streams.
- TestQuicClient.py / TestQuicServer.py: Test scripts for the client and server.
- TestStreamIn.py / TestStreamOut.py: Test scripts for stream modules.
- exp.py: Script to run experiments and analyze performance.
- wireshark_record.pcapng: Wireshark capture file for QUIC communication.
- QUIC.pdf / Theory.pdf: Reference documents on QUIC protocol and its theory.

## How to Run
1. Start the Server:
   `python QuicServer.py`

2. Start the Client:
   `python QuicClient.py`

## Testing
Run test scripts to verify functionality:
`python TestQuicClient.py`
`python TestQuicServer.py`

## Additional Notes
- Use exp.py to run performance experiments.
- Open wireshark_record.pcapng in Wireshark to analyze network traffic.
