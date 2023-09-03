import pytest

import pyspark.sql.functions as F
from pyspark.sql.types import (
    StructField,
    StructType,
    BooleanType,
    DateType,
    IntegerType,
    ArrayType,
    FloatType,
    StringType,
)

import quinn
from quinn.extensions import create_df # noqa: F401
from tests.conftest import auto_inject_fixtures
import chispa

import datetime
import uuid


@auto_inject_fixtures("spark")
def test_single_space(spark):
    df = spark.create_df(
        [
            ("  I like     fish  ", "I like fish"),
            ("    zombies", "zombies"),
            ("simpsons   cat lady", "simpsons cat lady"),
            (None, None),
        ],
        [
            ("words", StringType(), True),
            ("expected", StringType(), True),
        ],
    )
    actual_df = df.withColumn("words_single_spaced", quinn.single_space(F.col("words")))
    chispa.assert_column_equality(actual_df, "words_single_spaced", "expected")


def test_remove_all_whitespace(spark):
    df = spark.create_df(
        [
            ("  I like     fish  ", "Ilikefish"),
            ("    zombies", "zombies"),
            ("simpsons   cat lady", "simpsonscatlady"),
            (None, None),
        ],
        [
            ("words", StringType(), True),
            ("expected", StringType(), True),
        ],
    )
    actual_df = df.withColumn(
        "words_without_whitespace", quinn.remove_all_whitespace(F.col("words"))
    )
    chispa.assert_column_equality(actual_df, "words_without_whitespace", "expected")


def test_remove_non_word_characters(spark):
    df = spark.create_df(
        [
            ("I?like!fish>", "Ilikefish"),
            ("%%%zombies", "zombies"),
            ("si%$#@!#$!@#mpsons", "simpsons"),
            (None, None),
        ],
        [
            ("words", StringType(), True),
            ("expected", StringType(), True),
        ],
    )
    actual_df = df.withColumn(
        "words_without_nonword_chars", quinn.remove_non_word_characters(F.col("words"))
    )
    chispa.assert_column_equality(actual_df, "words_without_nonword_chars", "expected")


def test_anti_trim(spark):
    df = spark.create_df(
        [
            ("  I like     fish  ", "  Ilikefish  "),
            ("    zombies", "    zombies"),
            ("  simpsons   cat lady   ", "  simpsonscatlady   "),
            (None, None),
        ],
        [
            ("words", StringType(), True),
            ("expected", StringType(), True),
        ],
    )
    actual_df = df.withColumn("words_anti_trimmed", quinn.anti_trim(F.col("words")))
    chispa.assert_column_equality(actual_df, "words_anti_trimmed", "expected")


def test_exists(spark):
    df = spark.createDataFrame(
        [
            ([1, 2, 3], False),
            ([4, 5, 6], True),
            ([10, 11, 12], True),
        ],
        StructType(
            [
                StructField("nums", ArrayType(IntegerType(), True), True),
                StructField("expected", BooleanType(), True),
            ]
        ),
    )
    actual_df = df.withColumn(
        "any_num_greater_than_5", quinn.exists(lambda n: n > 5)(F.col("nums"))
    )
    chispa.assert_column_equality(actual_df, "any_num_greater_than_5", "expected")


def test_forall(spark):
    df = spark.createDataFrame(
        [
            ([1, 2, 3], False),
            ([4, 5, 6], True),
            ([10, 11, 12], True),
        ],
        StructType(
            [
                StructField("nums", ArrayType(IntegerType(), True), True),
                StructField("expected", BooleanType(), True),
            ]
        ),
    )
    actual_df = df.withColumn(
        "all_nums_greater_than_3", quinn.forall(lambda n: n > 3)(F.col("nums"))
    )
    chispa.assert_column_equality(actual_df, "all_nums_greater_than_3", "expected")


def test_multi_equals(spark):
    df = spark.create_df(
        [
            ("cat", "cat", True),
            ("cat", "dog", False),
            ("pig", "pig", False),
            ("", "", False),
            (None, None, False),
        ],
        [
            ("s1", StringType(), True),
            ("s2", StringType(), True),
            ("expected", BooleanType(), True),
        ],
    )
    actual_df = df.withColumn(
        "are_s1_and_s2_cat", quinn.multi_equals("cat")(F.col("s1"), F.col("s2"))
    )
    chispa.assert_column_equality(actual_df, "are_s1_and_s2_cat", "expected")


def describe_week_start_date():
    def it_works_with_start_date_of_monday(spark):
        df = spark.create_df(
            [
                # converts a Thursday to the Monday before
                (datetime.datetime(2020, 1, 2), datetime.datetime(2019, 12, 30)),
                # converts a Wednesday to the Monday before
                (datetime.datetime(2020, 7, 15), datetime.datetime(2020, 7, 13)),
                # doesn't change if the day in a Monday
                (datetime.datetime(2020, 7, 20), datetime.datetime(2020, 7, 20)),
                (None, None),
            ],
            [("some_date", DateType(), True), ("expected", DateType(), True)],
        )
        actual_df = df.withColumn(
            "week_start_date", quinn.week_start_date(F.col("some_date"), "Mon")
        )
        chispa.assert_column_equality(actual_df, "week_start_date", "expected")

    def it_defaults_to_sunday_start_date(spark):
        df = spark.create_df(
            [
                # converts a Tuesday to the Sunday before
                (datetime.datetime(2020, 1, 2), datetime.datetime(2019, 12, 29)),
                # converts a Wednesday to the Sunday before
                (datetime.datetime(2020, 7, 15), datetime.datetime(2020, 7, 12)),
                # doesn't change if the day is Sunday
                (datetime.datetime(2020, 7, 26), datetime.datetime(2020, 7, 26)),
                (None, None),
            ],
            [("some_date", DateType(), True), ("expected", DateType(), True)],
        )
        actual_df = df.withColumn(
            "week_start_date", quinn.week_start_date(F.col("some_date"))
        )
        chispa.assert_column_equality(actual_df, "week_start_date", "expected")

    def it_errors_out_if_with_invalid_week_start_date(spark):
        df = spark.create_df(
            [
                (datetime.datetime(2020, 1, 2), datetime.datetime(2019, 12, 29)),
            ],
            [("some_date", DateType(), True), ("expected", DateType(), True)],
        )
        with pytest.raises(ValueError) as excinfo:
            df.withColumn(
                "week_start_date", quinn.week_start_date(F.col("some_date"), "hello")
            )
        assert (
            excinfo.value.args[0]
            == "The day you entered 'hello' is not valid.  Here are the valid days: [Mon,Tue,Wed,Thu,Fri,Sat,Sun]"
        )


def describe_week_end_date():
    def it_works_with_end_date_of_sunday(spark):
        df = spark.create_df(
            [
                # converts a Thursday to the Sunday after
                (datetime.datetime(2020, 1, 2), datetime.datetime(2020, 1, 5)),
                # converts a Wednesday to the Sunday after
                (datetime.datetime(2020, 7, 15), datetime.datetime(2020, 7, 19)),
                # doesn't change if the day in a Sunday
                (datetime.datetime(2020, 7, 19), datetime.datetime(2020, 7, 19)),
                (None, None),
            ],
            [("some_date", DateType(), True), ("expected", DateType(), True)],
        )
        actual_df = df.withColumn(
            "week_start_date", quinn.week_end_date(F.col("some_date"), "Sun")
        )
        chispa.assert_column_equality(actual_df, "week_start_date", "expected")

    def it_defaults_to_saturday_week_end(spark):
        df = spark.create_df(
            [
                # converts a Tuesday to the Saturday after
                (datetime.datetime(2020, 1, 2), datetime.datetime(2020, 1, 4)),
                # converts a Wednesday to the Saturday after
                (datetime.datetime(2020, 7, 15), datetime.datetime(2020, 7, 18)),
                # doesn't change if the day is Saturday
                (datetime.datetime(2020, 7, 25), datetime.datetime(2020, 7, 25)),
                (None, None),
            ],
            [("some_date", DateType(), True), ("expected", DateType(), True)],
        )
        actual_df = df.withColumn(
            "week_start_date", quinn.week_end_date(F.col("some_date"))
        )
        chispa.assert_column_equality(actual_df, "week_start_date", "expected")

    def it_errors_out_if_with_invalid_week_end_date(spark):
        df = spark.create_df(
            [
                (datetime.datetime(2020, 1, 2), datetime.datetime(2019, 12, 29)),
            ],
            [("some_date", DateType(), True), ("expected", DateType(), True)],
        )
        with pytest.raises(ValueError) as excinfo:
            df.withColumn(
                "week_start_date", quinn.week_end_date(F.col("some_date"), "Friday")
            )
        assert (
            excinfo.value.args[0]
            == "The day you entered 'Friday' is not valid.  Here are the valid days: [Mon,Tue,Wed,Thu,Fri,Sat,Sun]"
        )


def describe_approx_equal():
    def it_works_with_floating_values(spark):
        df = spark.create_df(
            [
                (1.1, 1.05, True),
                (1.1, 11.6, False),
                (1.02, 1.09, True),
                (1.02, 1.34, False),
                (None, None, None),
            ],
            [
                ("num1", FloatType(), True),
                ("num2", FloatType(), True),
                ("expected", BooleanType(), True),
            ],
        )
        actual_df = df.withColumn(
            "are_nums_approx_equal",
            quinn.approx_equal(F.col("num1"), F.col("num2"), F.lit(0.1)),
        )
        chispa.assert_column_equality(actual_df, "are_nums_approx_equal", "expected")

    def it_works_with_integer_values(spark):
        df = spark.create_df(
            [
                (12, 14, True),
                (20, 26, False),
                (44, 41, True),
                (32, 9, False),
                (None, None, None),
            ],
            [
                ("num1", IntegerType(), True),
                ("num2", IntegerType(), True),
                ("expected", BooleanType(), True),
            ],
        )
        actual_df = df.withColumn(
            "are_nums_approx_equal",
            quinn.approx_equal(F.col("num1"), F.col("num2"), F.lit(5)),
        )
        chispa.assert_column_equality(actual_df, "are_nums_approx_equal", "expected")


def test_array_choice(spark):
    df = spark.create_df(
        [(["a", "b", "c"],), (["a", "b", "c", "d"],), (["x"],), ([None],)],
        [("letters", ArrayType(StringType(), True), True)],
    )
    actual_df = df.withColumn("random_letter", quinn.array_choice(F.col("letters")))
    # actual_df.show()
    # chispa.assert_column_equality(actual_df, "are_nums_approx_equal", "expected")

    # df = spark.createDataFrame([('a',), ('b',), ('c',)], ['letter'])
    # df.show()
    # cols = list(map(lambda c: F.lit(c), ['Retail', 'SME', 'Cor']))
    # df.withColumn('business_vertical', quinn.array_choice(F.array(cols))).show()


def test_regexp_extract_all(spark):
    df = spark.create_df(
        [("200 - 300 PA.", ["200", "300"]), ("400 PA.", ["400"]), (None, None)],
        [
            ("str", StringType(), True),
            ("expected", ArrayType(StringType(), True), True),
        ],
    )
    actual_df = df.withColumn(
        "all_numbers", quinn.regexp_extract_all(F.col("str"), F.lit(r"(\d+)"))
    )
    chispa.assert_column_equality(actual_df, "all_numbers", "expected")


def test_business_days_between(spark):
    df = spark.create_df(
        [
            (datetime.datetime(2020,12,23), datetime.datetime(2021,1,2), 7),
            (datetime.datetime(2020,12,23), datetime.datetime(2021,1,5), 9),
            (datetime.datetime(2020,12,23), datetime.datetime(2019,1,5), 512),
            (datetime.datetime(2020,12,23), datetime.datetime(2020,12,23), 0),
            (datetime.datetime(2020,12,23), None, None),
            (None, None, None)
        ],
        [
            ("start_date", DateType(), True),
            ("end_date", DateType(), True),
            ("expected", IntegerType(), True)
        ],
    )
    actual_df = df.withColumn(
        "business_days_between",
        quinn.business_days_between(F.col("start_date"),F.col("end_date"))
    )
    chispa.assert_column_equality(actual_df, "business_days_between", "expected")

def describe_uuid5():
    def test_no_extra_string(spark):
        df = spark.create_df(
            [
                # Manually calculated with Namespace: animals.com, no extra string argument.
                ("cat", "c04e5a9e-8088-5d64-8b81-26e74ede56f8"),
                ("dog", "08d3c582-5d77-5bb0-8eeb-b415942c67cd"),
                ("pig", "58baf419-4019-5f7f-bbf1-54af269c57df"),
            ],
            [
                ("s1", StringType(), True),
                ("expected", StringType(), True),
            ],
        )
        actual_df = df.withColumn(
            "uuid5_of_s1", quinn.uuid5(F.col("s1"), namespace=uuid.uuid5(uuid.NAMESPACE_DNS, "animals.com"))
        )
        chispa.assert_column_equality(actual_df, "uuid5_of_s1", "expected")

    def test_with_extra_string(spark):
        df = spark.create_df(
            [
                # Manually calculated with Namespace: animals.com, "domesticated" as extra string.
                ("cat", "d433fd86-8cc9-50b0-a53e-a285f6873c18"),
                ("dog", "af2dbcba-7a71-574c-92a6-f501b43c6266"),
                ("pig", "c06bb8b8-1889-5018-adc1-4d73e943b985"),
            ],
            [
                ("s1", StringType(), True),
                ("expected", StringType(), True),
            ],
        )
        actual_df = df.withColumn(
            "uuid5_of_s1",
            quinn.uuid5(
                F.col("s1"), namespace=uuid.uuid5(uuid.NAMESPACE_DNS, "animals.com"), extra_string="domesticated"
            )
        )
        chispa.assert_column_equality(actual_df, "uuid5_of_s1", "expected")
