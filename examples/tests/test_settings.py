# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 18:46'

from flask import request
import re
import traceback


# from sprite.settings import Settings
#
#
#
#
#
# if __name__ == '__main__':
#     class TestDict:
#         def __init__(self):
#             pass
#
#     test_settings_dict = {
#         "name":"liyong",
#         "test":TestDict(),
#     }
#
#     settings = Settings(values=test_settings_dict)
#     print(settings.get("test"))
#     print(settings.getdict("HEADERS"))
#     print(settings.get("MOSTSTOP"))
#     print(settings.getint("MAXCOROUTINEAMOUNT"))


class ImportWellChosenFeature:
    @classmethod
    def parse_csv_file(cls, file):
        # from src.utils.log import Log
        # Log.info(file.getvalue())
        well_chosen_feature_list = {}
        invalid_well_chosen_feature_list = []
        allow_metric_key_list = ["psi", "iv", "countDistinct", "max", "min", "ave", "mse", "nozero", "nonull"]
        source_table_pattern = re.compile(r"^\w+::\w+$")
        metric_value_pattern = re.compile(r"^\d+\.\d+$")
        num_row = 1
        try:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                reason = []
                if not cls.check_source_table(row["source_table"], source_table_pattern):
                    reason.append(u"精选特征source_table[%s]不合法" % row["source_table"])
                well_chosen_feature = {"feature_name": row["feature_name"], "source_table": row["source_table"],
                                       "default_value": row["default_value"], "metrics": []}
                for metric in row["metrics"].split("|"):
                    metric = metric.split(":")
                    metric_key = metric[0]
                    metric_value = metric[1]
                    well_chosen_feature["metrics"].append({
                        "metric_key": metric_key,
                        "metric_value": metric_value
                    })
                    if not cls.check_metric_key(metric_key, allow_metric_key_list):
                        reason.append(u"精选特征指标metric_key[%s]不合法" % metric_key)
                    if not cls.check_metric_value(metric_value, metric_value_pattern):
                        reason.append(u"精选特征指标metric_value[%s对应的%s]不合法" % (metric_key, metric_value))
                if row["feature_name"] in well_chosen_feature_list:
                    reason.append(u"精选特征名称重复")
                if len(reason) != 0:
                    reason = "\n".join(reason)
                    well_chosen_feature["reason"] = reason
                    invalid_well_chosen_feature_list.append(well_chosen_feature)
                else:
                    well_chosen_feature_list[row["feature_name"]] = well_chosen_feature

        except Exception:
            print(traceback.format_exc())
            raise Exception(1000, u"parse csv file failed, incorrect format",
                                u"解析csv文件出错, 在第%d行，请检查文件格式是否符合以下标准:\n%s\n%s" % (
                                    num_row,
                                    "feature_name,source_table,default_value,metrics",
                                    "pay_total_money_avg_woe,wechat_pay_base::t_xxx_xxx,0,psi:0.3|iv:0.3"
                                ))
        return list(well_chosen_feature_list.values()), invalid_well_chosen_feature_list

    @classmethod
    def check_source_table(cls, source_table, source_table_pattern):
        result = source_table_pattern.search(source_table)
        return bool(result)

    @classmethod
    def check_metric_key(cls, metric_key, allow_metric_key_list):
        if metric_key not in allow_metric_key_list:
            return False
        return True

    @classmethod
    def check_metric_value(cls, metric_value, metric_value_pattern):
        result = metric_value_pattern.search(metric_value)
        return bool(result)

import csv
from io import BytesIO

with open("/Users/liyong/projects/open_source/sprite/examples/tests/test_well_chosen_features_file.csv") as f:
    file = BytesIO()
    while True:
        buff = f.read(1024)
        if not buff:
            break
        file.write(buff.encode("utf-8"))
    well_chosen_feature, invalid_well_chosen_feature = ImportWellChosenFeature.parse_csv_file(file.getvalue().decode("utf-8").split("\n"))
    print(well_chosen_feature)
    print(invalid_well_chosen_feature)








