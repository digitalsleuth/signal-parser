# Signal Parser
This tool is designed to provide a web-based view of the contents of the Signal Messenger application.

It also parses the contents into JSON files which can be ingested into many other tool-sets.

## Usage

```bash
usage: signal_parser.py [-h] -d SIGNAL_DIR -o OUTPUT_DIR [-l] [-w [IP_ADDR]]

Signal DB Parser v1.1.0

optional arguments:
  -h, --help            show this help message and exit
  -d SIGNAL_DIR, --dir SIGNAL_DIR
                        the Signal data directory
  -o OUTPUT_DIR, --output OUTPUT_DIR
                        the location for storing processed data
  -l, --load            load pre-processed data - does not re-process, requires -w, -o, -d
  -w [IP_ADDR], --web [IP_ADDR]
                        launch the web interface after parsing, specify the IP address to use
```
