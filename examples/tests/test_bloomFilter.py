# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 11:29'



from sprite.utils.pybloomfilter import BloomFilter



if __name__ == '__main__':
    b = BloomFilter(capacity=100)
    b.add("test")
    result = "test" in b
    result_tow = "test_two" in b
    print(result)
    print(result_tow)