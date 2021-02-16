from typing import Dict, Set, List, Tuple, Any
import enum
import math
import sys

import pytest

import msgspec


class FruitInt(enum.IntEnum):
    APPLE = 1
    BANANA = 2


class FruitStr(enum.Enum):
    APPLE = "apple"
    BANANA = "banana"


INTS = [
    -(2 ** 63),
    -(2 ** 31 + 1),
    -(2 ** 31),
    -(2 ** 15 + 1),
    -(2 ** 15),
    -(2 ** 7 + 1),
    -(2 ** 7),
    -(2 ** 5 + 1),
    -(2 ** 5),
    -1,
    0,
    1,
    2 ** 7 - 1,
    2 ** 7,
    2 ** 8 - 1,
    2 ** 8,
    2 ** 16 - 1,
    2 ** 16,
    2 ** 32 - 1,
    2 ** 32,
    2 ** 64 - 1,
]

FLOATS = [
    -1.5,
    0.0,
    1.5,
    -float("inf"),
    float("inf"),
    float("nan"),
    sys.float_info.max,
    sys.float_info.min,
    -sys.float_info.max,
    -sys.float_info.min,
]

SIZES = [0, 1, 31, 32, 2 ** 8 - 1, 2 ** 8, 2 ** 16 - 1, 2 ** 16]


def assert_eq(x, y):
    if isinstance(x, float) and math.isnan(x):
        assert math.isnan(y)
    else:
        assert x == y


class TestEncoderErrors:
    @pytest.mark.parametrize("x", [-(2 ** 63) - 1, 2 ** 64])
    def test_encode_integer_limits(self, x):
        enc = msgspec.Encoder()
        with pytest.raises(OverflowError):
            enc.encode(x)

    def rec_obj1(self):
        o = []
        o.append(o)
        return o

    def rec_obj2(self):
        o = ([],)
        o[0].append(o)
        return o

    def rec_obj3(self):
        o = {}
        o["a"] = o
        return o

    def rec_obj4(self):
        class Box(msgspec.Struct):
            a: "Box"

        o = Box(None)
        o.a = o
        return o

    @pytest.mark.parametrize("case", [1, 2, 3, 4])
    def test_encode_infinite_recursive_object_errors(self, case):
        enc = msgspec.Encoder()
        o = getattr(self, "rec_obj%d" % case)()
        with pytest.raises(RecursionError):
            enc.encode(o)


class TestTypedDecoder:
    def check_unexpected_type(self, dec_type, val, msg):
        dec = msgspec.Decoder(dec_type)
        s = msgspec.Encoder().encode(val)
        with pytest.raises(TypeError, match=msg):
            dec.decode(s)

    def test_none(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(None)
        assert dec.decode(enc.encode(None)) is None
        with pytest.raises(TypeError, match="expected `None`"):
            assert dec.decode(enc.encode(1))

    @pytest.mark.parametrize("x", [False, True])
    def test_bool(self, x):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(bool)
        assert dec.decode(enc.encode(x)) is x

    def test_bool_unexpected_type(self):
        self.check_unexpected_type(bool, "a", "expected `bool`")

    @pytest.mark.parametrize("x", INTS)
    def test_int(self, x):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(int)
        assert dec.decode(enc.encode(x)) == x

    def test_int_unexpected_type(self):
        self.check_unexpected_type(int, "a", "expected `int`")

    @pytest.mark.parametrize("x", FLOATS + INTS)
    def test_float(self, x):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(float)
        res = dec.decode(enc.encode(x))
        sol = float(x)
        if math.isnan(sol):
            assert math.isnan(res)
        else:
            assert res == sol

    def test_float_unexpected_type(self):
        self.check_unexpected_type(float, "a", "expected `float`")

    @pytest.mark.parametrize("size", SIZES)
    def test_str(self, size):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(str)
        x = "a" * size
        res = dec.decode(enc.encode(x))
        assert res == x

    def test_str_unexpected_type(self):
        self.check_unexpected_type(str, 1, "expected `str`")

    @pytest.mark.parametrize("size", SIZES)
    def test_bytes(self, size):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(bytes)
        x = b"a" * size
        res = dec.decode(enc.encode(x))
        assert isinstance(res, bytes)
        assert res == x

    def test_bytes_unexpected_type(self):
        self.check_unexpected_type(bytes, 1, "expected `bytes`")

    @pytest.mark.parametrize("size", SIZES)
    def test_bytearray(self, size):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(bytearray)
        x = bytearray(size)
        res = dec.decode(enc.encode(x))
        assert isinstance(res, bytearray)
        assert res == x

    def test_bytearray_unexpected_type(self):
        self.check_unexpected_type(bytearray, 1, "expected `bytearray`")

    @pytest.mark.parametrize("size", SIZES)
    def test_list_lengths(self, size):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(list)
        x = list(range(size))
        res = dec.decode(enc.encode(x))
        assert res == x

    @pytest.mark.parametrize("typ", [list, List, List[Any]])
    def test_list_any(self, typ):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(typ)
        x = [1, "two", b"three"]
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `list`"):
            dec.decode(enc.encode(1))

    def test_list_typed(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(List[int])
        x = [1, 2, 3]
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `int`"):
            dec.decode(enc.encode([1, 2, "three"]))

    @pytest.mark.parametrize("size", SIZES)
    def test_set_lengths(self, size):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(set)
        x = set(range(size))
        res = dec.decode(enc.encode(x))
        assert res == x

    @pytest.mark.parametrize("typ", [set, Set, Set[Any]])
    def test_set_any(self, typ):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(typ)
        x = {1, "two", b"three"}
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `set`"):
            dec.decode(enc.encode(1))

    def test_set_typed(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(Set[int])
        x = {1, 2, 3}
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `int`"):
            dec.decode(enc.encode({1, 2, "three"}))

    @pytest.mark.parametrize("size", SIZES)
    def test_vartuple_lengths(self, size):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(tuple)
        x = tuple(range(size))
        res = dec.decode(enc.encode(x))
        assert res == x

    @pytest.mark.parametrize("typ", [tuple, Tuple, Tuple[Any, ...]])
    def test_vartuple_any(self, typ):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(typ)
        x = (1, "two", b"three")
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `tuple`"):
            dec.decode(enc.encode(1))

    def test_vartuple_typed(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(Tuple[int, ...])
        x = (1, 2, 3)
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `int`"):
            dec.decode(enc.encode((1, 2, "three")))

    def test_fixtuple_any(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(Tuple[Any, Any, Any])
        x = (1, "two", b"three")
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `tuple`"):
            dec.decode(enc.encode(1))
        with pytest.raises(ValueError, match="Expected tuple of length 3"):
            dec.decode(enc.encode((1, 2)))

    def test_fixtuple_typed(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(Tuple[int, str, bytes])
        x = (1, "two", b"three")
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `bytes`"):
            dec.decode(enc.encode((1, "two", "three")))
        with pytest.raises(ValueError, match="Expected tuple of length 3"):
            dec.decode(enc.encode((1, 2)))

    @pytest.mark.parametrize("size", SIZES)
    def test_dict_lengths(self, size):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(dict)
        x = {i: i for i in range(size)}
        res = dec.decode(enc.encode(x))
        assert res == x

    @pytest.mark.parametrize("typ", [dict, Dict, Dict[Any, Any]])
    def test_dict_any_any(self, typ):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(typ)
        x = {1: "one", "two": 2, b"three": 3.0}
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `dict`"):
            dec.decode(enc.encode(1))

    def test_dict_any_val(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(Dict[str, Any])
        x = {"a": 1, "b": "two", "c": b"three"}
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `str`"):
            dec.decode(enc.encode({1: 2}))

    def test_dict_any_key(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(Dict[Any, str])
        x = {1: "a", "two": "b", b"three": "c"}
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `str`"):
            dec.decode(enc.encode({1: 2}))

    def test_dict_typed(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(Dict[str, int])
        x = {"a": 1, "b": 2}
        res = dec.decode(enc.encode(x))
        assert res == x
        with pytest.raises(TypeError, match="expected `str`"):
            dec.decode(enc.encode({1: 2}))
        with pytest.raises(TypeError, match="expected `int`"):
            dec.decode(enc.encode({"a": "two"}))

    def test_enum(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(FruitStr)

        a = enc.encode(FruitStr.APPLE)
        assert enc.encode("APPLE") == a
        assert dec.decode(a) == FruitStr.APPLE

        with pytest.raises(ValueError, match="truncated"):
            dec.decode(a[:-2])
        with pytest.raises(TypeError, match="Error decoding enum `FruitStr`"):
            dec.decode(enc.encode("MISSING"))
        with pytest.raises(TypeError):
            dec.decode(enc.encode(1))

    def test_int_enum(self):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder(FruitInt)

        a = enc.encode(FruitInt.APPLE)
        assert enc.encode(1) == a
        assert dec.decode(a) == FruitInt.APPLE

        with pytest.raises(ValueError, match="truncated"):
            dec.decode(a[:-2])
        with pytest.raises(TypeError, match="Error decoding enum `FruitInt`"):
            dec.decode(enc.encode(1000))
        with pytest.raises(TypeError):
            dec.decode(enc.encode("INVALID"))


class CommonTypeTestBase:
    """Test msgspec untyped encode/decode"""

    def test_none(self):
        self.check(None)

    @pytest.mark.parametrize("x", [False, True])
    def test_bool(self, x):
        self.check(x)

    @pytest.mark.parametrize("x", INTS)
    def test_int(self, x):
        self.check(x)

    @pytest.mark.parametrize("x", FLOATS)
    def test_float(self, x):
        self.check(x)

    @pytest.mark.parametrize("size", SIZES)
    def test_str(self, size):
        self.check(" " * size)

    @pytest.mark.parametrize("size", SIZES)
    def test_bytes(self, size):
        self.check(b" " * size)

    @pytest.mark.parametrize("size", SIZES)
    def test_dict(self, size):
        self.check({str(i): i for i in range(size)})

    @pytest.mark.parametrize("size", SIZES)
    def test_list(self, size):
        self.check(list(range(size)))


class TestUntypedRoundtripCommon(CommonTypeTestBase):
    """Check the untyped deserializer works for common types"""

    def check(self, x):
        enc = msgspec.Encoder()
        dec = msgspec.Decoder()
        assert_eq(dec.decode(enc.encode(x)), x)


class TestCompatibility(CommonTypeTestBase):
    """Test compatibility with the existing python msgpack library"""

    def check(self, x):
        msgpack = pytest.importorskip("msgpack")

        enc = msgspec.Encoder()
        dec = msgspec.Decoder()

        assert_eq(dec.decode(msgpack.dumps(x)), x)
        assert_eq(msgpack.loads(enc.encode(x)), x)
