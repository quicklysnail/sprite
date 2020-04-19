# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:50'

from collections import Mapping


class CaselessDict(dict):
    __slots__ = ()

    def __init__(self, seq=None):
        super(CaselessDict, self).__init__()
        if seq:
            self.update(seq)

    def __getitem__(self, key):
        return dict.__getitem__(self, self.normal_key(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, self.normal_key(key), self.normal_value(value))

    def __delitem__(self, key):
        dict.__delitem__(self, self.normal_key(key))

    def __contains__(self, key):
        return dict.__contains__(self, self.normal_key(key))

    has_key = __contains__

    def __copy__(self):
        return self.__class__(self)

    copy = __copy__

    def normal_key(self, key):
        """Method to normalize dictionary key access"""
        try:
            return key.lower()
        except TypeError:
            tmp_str = ""
            for c in key:
                try:
                    tmp_str += c.lower()
                except TypeError:
                    tmp_str += c
        return tmp_str

    def normal_value(self, value, key=None):
        """Method to normalize values prior to be setted"""
        return value

    def get(self, key, def_val=None):
        return dict.get(self, self.normal_key(key), self.normal_value(def_val))

    def setdefault(self, key, def_val=None):
        return dict.setdefault(self, self.normal_key(key), self.normal_value(def_val))

    def update(self, seq):
        seq = seq.items() if isinstance(seq, Mapping) else seq
        iseq = ((self.normal_key(k), self.normal_value(v)) for k, v in seq)
        super(CaselessDict, self).update(iseq)

    @classmethod
    def fromkeys(cls, keys, value=None):
        return cls((k, value) for k in keys)

    def pop(self, key, *args):
        return dict.pop(self, self.normal_key(key), *args)


class MultiValueDict(dict):
    def __init__(self, seq=None):
        super(MultiValueDict, self).__init__()
        if seq:
            self.update(seq)

    def __getitem__(self, key):
        try:
            origin_value = dict.__getitem__(self, key)
            value = origin_value[0]
            return value
        except (KeyError, IndexError):
            raise KeyError()

    def __setitem__(self, key, value):
        try:
            origin_value = dict.__getitem__(self, key)
            origin_value.append(value)
        except KeyError:
            origin_value = [value]
            dict.__setitem__(self, key, origin_value)

    def __delitem__(self, key):
        try:
            origin_value = dict.__getitem__(self, key)
            if len(origin_value) == 1:
                dict.__delitem__(self, key)
            else:
                origin_value.pop()
        except IndexError:
            dict.__delitem__(self, key)

    def __copy__(self):
        return self.__class__(self)

    copy = __copy__

    def get(self, key, def_val=None):
        try:
            value = self[key]
        except KeyError:
            value = def_val
        return value

    def setdefault(self, key, def_val=None):
        return dict.setdefault(self, key, def_val)

    @classmethod
    def fromkeys(cls, keys, value=None):
        return cls((k, value) for k in keys)

    def pop(self, key, *args):
        return dict.pop(self, key, *args)

    def view(self):
        for key, values in self.items():
            for value in values:
                yield key, value

    def update(self, seq):
        seq = seq.items() if isinstance(seq, Mapping) else seq
        new_seq = []
        for k, v in seq:
            v = [v]
            new_seq.append((k, v))
        super(MultiValueDict, self).update(new_seq)


if __name__ == "__main__":
    test_dict = MultiValueDict({"one": "liyong", "two": "tt"})
    # print(test_dict)
    test_dict['one'] = "liyong_tt"
    # print(test_dict.get("one"))
    for key, value in test_dict.view():
        print(key)
        print(value)
    # del test_dict["one"]
    # print(test_dict)
    # del test_dict["one"]
    # print(test_dict)
