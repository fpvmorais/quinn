import re
from typing import List


class ScalaToPyspark:
    def __init__(self: "ScalaToPyspark", scala_path: str) -> None:
        self.scala_path = scala_path

    def lines(self: "ScalaToPyspark") -> List[str]:
        with open(self.scala_path, "r") as text_file:
            result = text_file.readlines()

        # remove lines that start with package
        result = list(filter(lambda line: not line.startswith("package"), result))

        # replace common import statements
        result = [
            "from pyspark.sql.dataframe import DataFrame\n"
            if x.startswith("import org.apache.spark.sql.DataFrame")
            else x
            for x in result
        ]
        result = [
            "import pyspark.sql.functions as F\n"
            if x.startswith("import org.apache.spark.sql.functions")
            else x
            for x in result
        ]

        # remove scala import statements
        result = list(filter(lambda line: not line.startswith("import scala"), result))

        # remove the vals and vars
        result = [x.replace("val ", "") for x in result]
        result = [x.replace("var ", "") for x in result]

        # remove ending curly braces (low hanging fruit)
        result = list(filter(lambda line: line.strip() != "}", result))

        # clean up the function definitions
        result = [
            self.clean_function_definition(x) if x.lstrip().startswith("def") else x
            for x in result
        ]

        # prefix SQL functions with F
        result = [x.replace("col(", "F.col(") for x in result]

        # replace null with None
        result = [x.replace("null", "None") for x in result]

        # capital case true and false
        result = [x.replace("true", "True") for x in result]
        result = [x.replace("false", "False") for x in result]

        return result

    def display(self: "ScalaToPyspark") -> str:
        print("".join(self.lines()))

    def clean_function_definition(self: "ScalaToPyspark", s: str) -> str:
        m = re.search(r"(\s*)def (\w+).*\((.*)\)", s)
        if m:
            whitespace = m.group(1)
            method_name = m.group(2)
            args = m.group(3)
            cleaned_args = self.clean_args(args)
            return "{whitespace}def {method_name}({cleaned_args}):\n".format(
                whitespace=whitespace,
                method_name=method_name,
                cleaned_args=cleaned_args,
            )
        return s

    def clean_args(self: "ScalaToPyspark", args: str) -> str:
        unannoted_args_list = list(map(lambda a: a.split(": ")[0], args.split(", ")))
        return ", ".join(unannoted_args_list)
