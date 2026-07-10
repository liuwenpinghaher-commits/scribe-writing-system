---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers

In SurrealDB, numbers can be one of three types: 64-bit integers, 64-bit floating point numbers, or 128-bit decimal numbers.
##  Integer numbers[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#integer-numbers)
If a numeric value is specified without a decimal point and is within the range `-9223372036854775808` to `9223372036854775807` then the value will be parsed, stored, and treated as a 64-bit integer.

```surql
CREATE event SET year = 2022;
```

##  Floating point numbers[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#floating-point-numbers)
If a number value is specified with a decimal point, or is outside of the maximum range specified above, then the number will automatically be parsed, stored, and treated as a 64-bit floating point value. This ensures efficiency when performing mathematical calculations within SurrealDB.

```surql
CREATE event SET temperature = 41.5;
```

##  Decimal numbers[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#decimal-numbers)
To opt into 128-bit decimal numbers when specifying numeric values, you can use the `dec` suffix.

```surql
CREATE product SET price = 99.99dec;
```

The `dec` suffix is an instruction to the parser and not a cast, and is thus preferred when making a decimal.

```surql
-- Creates the imprecise float 3.888888888888889 and casts it into a decimal as 3.888888888888889dec
RETURN <decimal>3.8888888888888888;
-- Uses the input 3.8888888888888888 to directly create a decimal
RETURN 3.8888888888888888dec;
```

##  Using a specific numeric type[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#using-a-specific-numeric-type)
To use a specific type when specifying numeric values, you can cast the value to a specific numeric type or use the appropriate suffix.

```surql
CREATE event SET
	year = <int> 2022,
	temperature = <float> 41.5 + 5f,
	horizon = <decimal> 31 + 3dec
;
```

##  Numeric precision[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#numeric-precision)
Different numeric types can be compared and used together in calculations.
The benefits of floating point numeric values are speed and storage size, but there is a limit to the numeric precision.

```surql
RETURN 13.5719384719384719385639856394139476937756394756;

-- 13.571938471938472f
```

In addition, when using floating point numbers specifically, mathematical operations can result in a loss of precision (as is normal with other databases).

```surql
RETURN 0.3 + 0.3 + 0.3 + 0.1;

-- 0.9999999999999999f
```

Common rounding errors can be avoided by performing calculations using decimals.

```surql
RETURN 0.3dec + 0.3dec + 0.3dec + 0.1dec;

-- 1.0dec
```

##  Underscores[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#underscores)
As a convenience, underscores are ignored when using a number. This allows input to be more readable than it would otherwise. Because underscores are ignored, they will not display in the output.

```surql
RELATE dr:evil->bribes->other:character SET dollars = 1_000_000.99;
-- [{ dollars: 1000000.99, id: bribes:4bfld2ukwnja24dzrpw9, in: dr:evil, out: other:character }]

-- Input Korean currency counted in units of 10000, not 1000
RELATE korean:purchaser->buys_house_from->korean:seller
              -- 10억 4천만 5천
    SET amount = 10_4000_5000;
-- [{ amount: 1040005000, id: buys_house_from:9070t2ctgwwg202cpw1z, in: korean:purchaser, out: korean:seller }]
```

##  Mathematical constants[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#mathematical-constants)
A set of floating point numeric constants are available in SurrealDB. Constant names are case insensitive, and can be specified with either lowercase or capital letters, or a mixture of both.

```surql
CREATE circle SET circumference = 10;
UPDATE circle SET radius = circumference / ( 2 * MATH::PI );
```
  
| Constant  | Description  | Value  |  
| --- | --- | --- |  
| `MATH::E`  | Euler’s number (e)  | 2.718281828459045  |  
| `MATH::FRAC_1_PI`  | 1/π  | 0.3183098861837907  |  
| `MATH::FRAC_1_SQRT_2`  | 1/sqrt(2)  | 0.7071067811865476  |  
| `MATH::FRAC_2_PI`  | 2/π  | 0.6366197723675814  |  
| `MATH::FRAC_2_SQRT_PI`  | 2/sqrt(π)  | 1.1283791670955126  |  
| `MATH::FRAC_PI_2`  | π/2  | 1.5707963267948966  |  
| `MATH::FRAC_PI_3`  | π/3  | 1.0471975511965979  |  
| `MATH::FRAC_PI_4`  | π/4  | 0.7853981633974483  |  
| `MATH::FRAC_PI_6`  | π/6  | 0.5235987755982989  |  
| `MATH::FRAC_PI_8`  | π/8  | 0.39269908169872414  |  
| `MATH::INF`  | Positive infinity  | inf  |  
| `MATH::LN_10`  | ln(10)  | 2.302585092994046  |  
| `MATH::LN_2`  | ln(2)  | 0.6931471805599453  |  
| `MATH::LOG10_2`  |  log 10(2)  | 0.3010299956639812  |  
| `MATH::LOG10_E`  |  log 10(e)  | 0.4342944819032518  |  
| `MATH::LOG2_10`  |  log 2(10)  | 3.321928094887362  |  
| `MATH::LOG2_E`  |  log 2(e)  | 1.4426950408889634  |  
| `MATH::NEG_INF`  | Negative infinity  | -inf  |  
| `MATH::PI`  | Archimedes’ constant (π)  | 3.141592653589793  |  
| `MATH::SQRT_2`  | sqrt(2)  | 1.4142135623730951  |  
| `MATH::TAU`  | The full circle constant (τ)  | 6.283185307179586  |
