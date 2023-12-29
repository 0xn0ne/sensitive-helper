Reference: https://github.com/securing/DumpsterDiver

# Sensitive Helper

[简体中文](./README.md) | English

Regular expression-based data mining assistant for sensitive information on local files. If you want to search for sensitive data on the web page, you can export the sensitive data to the local search. Optimized the use of multi-threading a bit , optimized the use of configuration .

**Note**: If the default rules do not meet your matching needs, please adjust the `rules` part of the configs.yaml file to match.

# Quick start

### Required

+ python >= 3.6

In the project directory and use the following command to install the dependent libraries

```
$ pip3 install toml yaml
```

Or use the `requirement` parameter of the PIP to install the dependency library

```
$ pip3 install -r requirements.txt
```

### Basic usage

+ Use the `-t` parameter to search directly on the target path.

```python3 sensitive-helper.py -t <Your search file path>```

+ When you want to exclude some types of files, you can use the `-e` parameter to exclude the specified files. Note that regular expressions are used here to match file names, for example, the program may search for the following file /tmp/aaa.so, if you do not want to search for the `.so` file type, you can use the regular expression `. *so` The program will match the `aaa.so` string with the regular expression `. *so` to filter `so` format files.

```python3 sensitive-helper.py -t <Your search file path> -e ".*so" ".*gz"```

+ If you think the search is too slow, you can use the `-p` parameter to adjust the number of processes to search (default: 8) to increase the search speed, although Python's multiprocessing sucks, it's better than nothing!
+ **Note**: Computer performance is not good set do not over 20 process number, the program requires a lot of IO, memory operations, the computer may crash, such as my computer...

```python3 sensitive-helper.py -t <Your search file path> -p 20```

+ If you want to save the data, you can use the `-o` parameter to output the result file in json format.

```python3 sensitive-helper.py -t <Your search file path> -o results.json```

+ By default, when the program matches using regular expressions, it will quit searching the current file after matching 1 expression. You can use the `-a` parameter to force the program to match every regular expression, to find more potentially useful data.

```python3 sensitive-helper.py -t <Your search file path> -a```

**Note**: The program has built-in default matching rules, which are prioritized as follows: default configuration < configs.yaml configuration < user input configuration

### Usage

```
% python3 sensitive-helper.py -h                                                    
usage: sensitive-helper.py [-h] -t TARGET_PATH [-p PROCESS_NUMBER] [-c CONFIG] [-o OUTPUT] [-e EXCLUDE_FILES [EXCLUDE_FILES ...]] [-a]

    ███████╗███████╗███╗   ██╗███████╗██╗████████╗██╗██╗   ██╗███████╗
    ██╔════╝██╔════╝████╗  ██║██╔════╝██║╚══██╔══╝██║██║   ██║██╔════╝
    ███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║   ██║██║   ██║█████╗  
    ╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║   ██║╚██╗ ██╔╝██╔══╝  
    ███████║███████╗██║ ╚████║███████║██║   ██║   ██║ ╚████╔╝ ███████╗
    ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝
    v0.1.3
    by 0xn0ne, https://github.com/0xn0ne/sensitive-helper

optional arguments:
  -h, --help            show this help message and exit
  -t TARGET_PATH, --target-path TARGET_PATH
                        search for file paths or folder paths for sensitive cache (eg. ~/download/folder).
  -p PROCESS_NUMBER, --process-number PROCESS_NUMBER
                        number of program processes (default: 5).
  -c CONFIG_PATH, --config-path CONFIG_PATH
                        path to the yaml configuration file (default: configs.yaml).
  -o OUTPUT_FORMAT, --output-format OUTPUT_FORMAT
                        output file format, available formats json, csv (default: csv).
  -e EXCLUDE_FILES [EXCLUDE_FILES ...], --exclude-files EXCLUDE_FILES [EXCLUDE_FILES ...]
                        excluded files, using regular matching (eg. \.DS_Store .*bin .*doc).
  -a, --is-re-all       hit a single regular expression per file or match all regular expressions to exit the match loop.
  -s, --is-silent       silent mode: when turned on, no hit data will be output on the console. use a progress bar instead.
```

### Sample: Default Mode

```
$ python3 sensitive-helper.py -t "cache/" -a
[*] file loading...
[*] analyzing...

[+] group: FUZZY MATCH, match: AppId":"123456", file: cache/heapdump
[+] group: BASE64, match: ZjY2MTQyNDEtYTIyYS00YjNlLTg1NTgtOTQ4NmUwZDFkZjM1, file: cache/heapdump
[+] group: FUZZY MATCH, match: password":"123456", file: cache/heapdump
[+] group: FILE PATH, match: C:\Windows\system32\drivers, file: cache/heapdump-BAK
[+] group: URL, match: http://hello.world/123456.jpg, file: cache/heapdump-BAK  
total file number: 5
```

### Sample: Silent Mode

```
$ python3 sensitive-helper.py -t "cache/" -a -s
[*] file loading...
[*] analyzing...

53792/53792 [██████████████████████████████████████████] 00:28<00:00,1856.73it/s
total file number: 53792
```

# Q&A

+ Q: Why don't we do sensitive data search on web pages?
+ A: Because web pages are ever-changing, changing an API interface or a css or id may require updating the code, so it is better to export it to the local area and unify the data processing by using text recognition.
