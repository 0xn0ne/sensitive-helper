参考链接：<https://github.com/securing/DumpsterDiver>

# Sensitive Helper

简体中文 | [English](./README_EN.md)

最近项目要搜索本地的敏感数据工作太多了，网上用了一些工具效果一般，被老板DISS了很多次，当然也可能是我不会用，如：SO文件无法读取、多进程报错、配置看不懂、识别原理云里雾里等，想提issues的，但大家都要养家想想算了，自己改一个。

基于正则表达式的本地文件敏感信息数据挖掘助手。如果要搜索网页上的敏感数据，可以把敏感数据导出到本地再进行搜索。优化了一下多线程的使用，优化了配置的使用方式。

**注意**：如果默认规则不满足您的匹配需求，请自行调整 configs.yaml 文件中的 `rules` 部分内容进行匹配

# 快速开始

### 依赖

+ python >= 3.6

进入项目目录，使用以下命令安装依赖库

```bash
pip3 install toml PyYAML tqdm pandas rarfile py7zr openpyxl
```

或者使用 PIP 的 `requirement` 参数安装依赖库

```bash
pip3 install -r requirements.txt
```

### 基础用法

使用 `-t` 参数直接对目标路径进行搜索

```$ python3 sensitive-helper.py -t <你的搜索文件路径>```

当想要排除部分类型文件，可以使用 `-e` 参数排除指定的文件，要注意这里是使用正则表达式进行文件名匹配的，比如程序可能搜索到以下文件 /tmp/aaa.so，如果不想搜索 `.so` 文件类型，可以使用正则表达式 `.*so` 程序会将 `aaa.so` 字符串与正则表达式进行匹配 `.*so`，即可对 `so` 格式文件进行过滤

```$ python3 sensitive-helper.py -t <你的搜索文件路径> -e ".*so" ".*gz"```

如果觉得搜索速度太慢，可以使用 `-p` 参数调整搜索的进程数（默认为：5）以提高搜索速度，虽然Python 的多进程很差劲，但有总比没有好
**注意**：计算机性能不好设置不要超过20个进程数，程序涉及大量的IO、内存操作，计算机可能会崩溃，比如我的电脑。

```$ python3 sensitive-helper.py -t <你的搜索文件路径> -p 10```

有保存数据的需求话，可以使用 `-o` 参数输出 json 格式的结果文件

```$ python3 sensitive-helper.py -t <你的搜索文件路径> -o results.json```

默认情况下，程序使用正则表达式进行匹配的时候，匹配到 1 条表达式就会退出当前文件的搜索。可以使用 `-a` 参数，强制程序将每条正则表达式都匹配完毕，挖掘更多可能有用的数据

```$ python3 sensitive-helper.py -t <你的搜索文件路径> -a```

**注意**：程序内置默认匹配规则，规则优先级为：默认配置 < configs.yaml 配置 < 用户输入配置

### 使用说明

```
$ python3 sensitive-helper.py -h                                  
usage: sensitive-helper.py [-h] -t TARGET_PATH [-p PROCESS_NUMBER] [-c CONFIG_PATH] [-o OUTPUT_FORMAT] [-e EXCLUDE_FILES [EXCLUDE_FILES ...]] [-a] [-s]

    ███████╗███████╗███╗   ██╗███████╗██╗████████╗██╗██╗   ██╗███████╗
    ██╔════╝██╔════╝████╗  ██║██╔════╝██║╚══██╔══╝██║██║   ██║██╔════╝
    ███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║   ██║██║   ██║█████╗  
    ╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║   ██║╚██╗ ██╔╝██╔══╝  
    ███████║███████╗██║ ╚████║███████║██║   ██║   ██║ ╚████╔╝ ███████╗
    ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝
    v0.1.3
    by 0xn0ne, https://github.com/0xn0ne/sensitive-helper

options:
  -h, --help            显示帮助信息并退出程序
  -t TARGET_PATH, --target-path TARGET_PATH
                        搜索敏感信息的文件路径或文件夹路径（例如：~/download/folder）
  -p PROCESS_NUMBER, --process-number PROCESS_NUMBER
                        程序进程数（默认值：5）
  -c CONFIG_PATH, --config-path CONFIG_PATH
                        yaml 配置文件的路径（默认值：configs.yaml）
  -o OUTPUT_FORMAT, --output-format OUTPUT_FORMAT
                        输出文件格式，可用格式为 json、csv（默认值：csv）
  -e EXCLUDE_FILES [EXCLUDE_FILES ...], --exclude-files EXCLUDE_FILES [EXCLUDE_FILES ...]
                        排除的文件，使用正则匹配（例如：\.DS_Store .*bin .*doc）
  -a, --is-re-all       每个文件的被单个正则表达式规则后退出匹配循环，或匹配所有正则表达式才退出匹配循环
  -s, --is-silent       静默模式：开启后，命令行不会输出命中的信息，会使用进度条来显示进度
```

### 默认模式输出样例

```bash
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

### 静默模式输出样例

```bash
$ python3 sensitive-helper.py -t "cache/" -a -s
[*] file loading...
[*] analyzing...

53792/53792 [██████████████████████████████████████████] 00:28<00:00,1856.73it/s
total file number: 53792
```

# Q&A

+ Q：为什么不做网页的敏感数据搜索？
+ A：因为网页千变万化，改动一个API接口或是一个css或者id都可能要更新代码，不如导出到本地，统一使用文本识别的方式对数据处理。
