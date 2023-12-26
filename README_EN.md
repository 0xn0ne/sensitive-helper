Reference: https://github.com/securing/DumpsterDiver

# Sensitive Helper

[简体中文](./README.md) | English

Regular expression-based data mining assistant for sensitive information on local files. If you want to search for sensitive data on the web page, you can export the sensitive data to the local search. Optimized the use of multi-threading a bit , optimized the use of configuration .

**Note**: If the default rules do not meet your matching needs, please adjust the `re_groups` part of the configs.yaml file to match.

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

Use the `-t` parameter to search directly on the target path.

```python3 sensitive-helper.py -t <Your search file path>```

When you want to exclude some types of files, you can use the `-e` parameter to exclude the specified files. Note that regular expressions are used here to match file names, for example, the program may search for the following file /tmp/aaa.so, if you do not want to search for the `.so` file type, you can use the regular expression `. *so` The program will match the `aaa.so` string with the regular expression `. *so` to filter `so` format files.

```python3 sensitive-helper.py -t <Your search file path> -e ".*so" ".*gz"```

If you think the search is too slow, you can use the `-p` parameter to adjust the number of processes to search (default: 8) to increase the search speed, although Python's multiprocessing sucks, it's better than nothing!

```python3 sensitive-helper.py -t <Your search file path> -p 20```

If you want to save the data, you can use the `-o` parameter to output the result file in json format.

```python3 sensitive-helper.py -t <Your search file path> -o results.json```

By default, when the program matches using regular expressions, it will quit searching the current file after matching 1 expression. You can use the `-a` parameter to force the program to match every regular expression, to find more potentially useful data.

```python3 sensitive-helper.py -t <Your search file path> -a```

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
    v0.1.1
    by 0xn0ne, https://github.com/0xn0ne/sensitive-helper

optional arguments:
  -h, --help            show this help message and exit
  -t TARGET_PATH, --target-path TARGET_PATH
                        search for file paths or folder paths for sensitive data(eg. ~/download/folder).
  -p PROCESS_NUMBER, --process-number PROCESS_NUMBER
                        number of program processes(default number 8).
  -c CONFIG, --config CONFIG
                        path to the yaml configuration file(default configs.yaml).
  -o OUTPUT, --output OUTPUT
                        path to json output(default without output).
  -e EXCLUDE_FILES [EXCLUDE_FILES ...], --exclude-files EXCLUDE_FILES [EXCLUDE_FILES ...]
                        excluded files, using regular matching(eg. \.DS_Store .*bin .*doc).
  -a, --is-re-all-group
                        hit a single regular expression per file or match all regular expressions to exit the match loop.
```

# Sample

```
% python3 sensitive-helper.py -t /dex_decompile -a
[+] {'file': '/dex_decompile/10239423_dexfile_repair/s/h.java', 'group': regexp': '(ftp|https?):\\/\\/[\\w\\-_]+(\\.[\\w\\-_]+)+([\\w\\-\\.,@?^=%&amp;:/~\\+#]*[\\w\\-\\@?^=%&amp;/~\\+#])?', 'match': 'http://www.example.com/hello', 'extend': ''}
[+] {'file': '/dex_decompile/10211981_dexfile_repair/auth/auth.java': 'BASE64', 'regexp': '[0-9a-zA-Z/+-]{6,}={,2}', 'match': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9', 'extend': '{"alg":"HS256","typ":"JWT"}'}
[+] {'file': '/dex_decompile/10239423_dexfile_repair/s/bg.java', 'group':MATCH', 'regexp': 'PASS.{,20}[=:(]\\s*.{,128}', 'match': 'PassedByPoints());', 'extend': ''}
total file number: 68920
total time(s): 112.49523591995239
```

# Q&A

+ Q: Why don't we do sensitive data search on web pages?
+ A: Because web pages are ever-changing, changing an API interface or a css or id may require updating the code, so it is better to export it to the local area and unify the data processing by using text recognition.
