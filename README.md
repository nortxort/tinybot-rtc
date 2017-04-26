## Tinybot-rtc

An extension module for the pinylib-rtc module.

This version is bassicly the same as the original tinybot, some commands have been removed as they simply aren't available in this protocol, atleast not yet.

tinybot-rtc is an **example** as to how a tinychat bot *could* look like using the [pinylib-rtc](https://github.com/nortxort/pinylib-rtc) module as a base. It could be used as a template or it could be expanded with more features. It's all up to you how you would like to use it.

## Setting up

Examples shown here, assumes you are using windows.

tinybot-rtc was developed using [python 2.7.10](https://www.python.org/downloads/windows/ "python for windows") so this is the recomended python interpreter. If you do not already have that installed, install if from the link. Later versions of python should work to, as long as they are from the 2.7 family. With some changes, i believe it could be made to work with python 3 to.

### Requirements

tinybot-rtc reqires pinylib-rtc and its [requirements](https://github.com/nortxort/pinylib-rtc/blob/master/README.md#requirements "pinylib requirements").

Next download [pinylib-rtc](https://github.com/nortxort/pinylib-rtc/archive/master.zip "pinylib-rtc module") and [tinybot-rtc](https://github.com/nortxort/tinybot-rtc/archive/master.zip "pinylib-rtc extension module") and unpack them. Now copy the **contents of the folders in tinybot-rtc to the coresponding folders inside pinylib-rtc**. Meaning, the content of the folder named *e.g* util in tinybot-rtc should be placed in pinylib-rtc's util folder and so on. If a folder inside tinybot-rtc does not exist inside pinylib-rtc, then the whole folder and it's content is copied in to pinylib-rtc. Place the files in the root folder of tinybot-rtc in the root folder of pinylib-rtc, overwriting files if necessary.

## Run tinybot

Run tinybot-rtc by typing `python path\to\bot_client.py` in a command prompt.

## Submitting an issue.

Since i rarely use tinychat, not much testing have been done. For now i will keep the issues open, but there is probably a better chance of fixing an issue yourself.


## Author

* [nortxort](https://github.com/nortxort)

## License

The MIT License (MIT)

Copyright (c) 2017 nortxort

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice
shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, 
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Acknowledgments

*Thanks to the following people who in some way or another, has helped with this project*



