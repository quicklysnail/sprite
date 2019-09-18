# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 18:46'


from sprite.settings import Settings





if __name__ == '__main__':
    class TestDict:
        def __init__(self):
            pass

    test_settings_dict = {
        "name":"liyong",
        "test":TestDict(),
    }

    settings = Settings(values=test_settings_dict)
    print(settings.get("test"))
    print(settings.getdict("HEADERS"))
    print(settings.get("MOSTSTOP"))
    print(settings.getint("MAXCOROUTINEAMOUNT"))







