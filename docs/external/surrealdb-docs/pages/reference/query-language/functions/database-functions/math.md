---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/math"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/math"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/math

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/math

This page contains built-in functions and constants on the `math` module for analysing numeric data and numeric collections.
##  Math functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#math-functions)  
| Function  | Description  |  
| --- | --- |  
| [`math::abs()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathabs)  | Returns the absolute value of a number  |  
| [`math::acos()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathacos)  | Computes the arccosine (inverse cosine) of a value  |  
| [`math::acot()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathacot)  | Computes the arccotangent (inverse cotangent) of an angle given in radians  |  
| [`math::asin()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathasin)  | Computes the arcsine (inverse sine) of a value  |  
| [`math::atan()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathatan)  | Computes the arctangent (inverse tangent) of a value  |  
| [`math::bottom()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathbottom)  | Returns the bottom X set of numbers in a set of numbers  |  
| [`math::ceil()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathceil)  | Rounds a number up to the next largest integer  |  
| [`math::clamp()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathclamp)  | Clamps a value between a specified minimum and maximum  |  
| [`math::cos()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathcos)  | Computes the cosine of an angle given in radians  |  
| [`math::cot()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathcot)  | Computes the cotangent of an angle given in radians  |  
| [`math::deg2rad()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathdeg2rad)  | Converts an angle from degrees to radians  |  
| [`math::fixed()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfixed)  | Returns a number with the specified number of decimal places  |  
| [`math::floor()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfloor)  | Rounds a number down to the nearest integer  |  
| [`math::interquartile()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathinterquartile)  | Returns the interquartile of an array of numbers  |  
| [`math::lerp()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlerp)  | Linearly interpolates between two values based on a factor  |  
| [`math::lerpangle()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlerpangle)  | Linearly interpolates between two angles in degrees  |  
| [`math::ln()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathln)  | Computes the natural logarithm (base e) of a value  |  
| [`math::log()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog)  | Computes the logarithm of a value with the specified base  |  
| [`math::log10()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog10)  | Computes the base-10 logarithm of a value  |  
| [`math::log2()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog2)  | Computes the base-2 logarithm of a value  |  
| [`math::max()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmax)  | Returns the greatest number from an array of numbers  |  
| [`math::mean()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmean)  | Returns the mean of a set of numbers  |  
| [`math::median()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmedian)  | Returns the median of a set of numbers  |  
| [`math::midhinge()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmidhinge)  | Returns the midhinge of a set of numbers  |  
| [`math::min()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmin)  | Returns the least number from an array of numbers  |  
| [`math::mode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmode)  | Returns the value that occurs most often in a set of numbers  |  
| [`math::nearestrank()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathnearestrank)  | Returns the nearest rank of an array of numbers  |  
| [`math::percentile()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathpercentile)  | Returns the value below which a percentage of data falls  |  
| [`math::pow()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathpow)  | Returns a number raised to a power  |  
| [`math::product()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathproduct)  | Returns the product of a set of numbers  |  
| [`math::rad2deg()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathrad2deg)  | Converts an angle from radians to degrees  |  
| [`math::round()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathround)  | Rounds a number up or down to the nearest integer  |  
| [`math::sign()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsign)  | Returns the sign of a value (-1, 0, or 1)  |  
| [`math::sin()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsin)  | Computes the sine of an angle given in radians  |  
| [`math::spread()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathspread)  | Returns the spread of an array of numbers  |  
| [`math::sqrt()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsqrt)  | Returns the square root of a number  |  
| [`math::stddev()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathstddev)  | Calculates how far a set of numbers are away from the mean  |  
| [`math::sum()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsum)  | Returns the total sum of a set of numbers  |  
| [`math::tan()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtan)  | Computes the tangent of an angle given in radians.  |  
| [`math::top()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtop)  | Returns the top X set of numbers in a set of numbers  |  
| [`math::trimean()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtrimean)  | The weighted average of the median and the two quartiles  |  
| [`math::variance()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathvariance)  | Calculates how far a set of numbers are spread out from the mean  |  
##  Math constants[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#math-constants)  
| Constant  | Description  |  
| --- | --- |  
| [`math::e`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathe)  | Constant representing the base of the natural logarithm (Euler's number)  |  
| [`math::frac_1_pi`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_1_pi)  | Constant representing the fraction 1/π  |  
| [`math::frac_1_sqrt_2`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_1_sqrt_2)  | Constant representing the fraction 1/sqrt(2)  |  
| [`math::frac_2_pi`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_2_pi)  | Constant representing the fraction 2/π  |  
| [`math::frac_2_sqrt_pi`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_2_sqrt_pi)  | Constant representing the fraction 2/sqrt(π)  |  
| [`math::frac_pi_2`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_2)  | Constant representing the fraction π/2  |  
| [`math::frac_pi_3`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_3)  | Constant representing the fraction π/3  |  
| [`math::frac_pi_4`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_4)  | Constant representing the fraction π/4  |  
| [`math::frac_pi_6`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_6)  | Constant representing the fraction π/6  |  
| [`math::frac_pi_8`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_8)  | Constant representing the fraction π/8  |  
| [`math::infinity`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathinf)  | Constant representing positive infinity  |  
| [`math::ln_10`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathln_10)  | Constant representing the natural logarithm (base e) of 10  |  
| [`math::ln_2`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathln_2)  | Constant representing the natural logarithm (base e) of 2  |  
| [`math::log10_2`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog10_2)  | Constant representing the base-10 logarithm of 2  |  
| [`math::log10_e`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog10_e)  | Constant representing the base-10 logarithm of e, the base of the natural logarithm (Euler’s number)  |  
| [`math::log2_10`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog2_10)  | Constant representing the base-2 logarithm of 10  |  
| [`math::log2_e`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog2_e)  | Constant representing the base-2 logarithm of e, the base of the natural logarithm (Euler’s number)  |  
| [`math::neg_infinity`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathneg_inf)  | Constant representing negative infinity  |  
| [`math::pi`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathpi)  | Constant representing the mathematical constant π.  |  
| [`math::sqrt_2`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsqrt_2)  | Constant representing the square root of 2  |  
| [`math::tau`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtau)  | Represents the mathematical constant τ, which is equal to 2π  |  
##  `math::abs`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathabs)
The `math::abs` function returns the absolute value of a number.
API DEFINITION

```surql
math::abs(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::abs(-13.746189);

-- 13.746189f
```

  

##  `math::acos`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathacos)
The `math::acos` function returns the arccosine (inverse cosine) of a number, which must be in the range -1 to 1. The result is expressed in radians.
API DEFINITION

```surql
math::acos(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::acos(0.5);

-- 1.0471975511965976f
```

  

##  `math::acot`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathacot)
The `math::acot` function returns the arccotangent (inverse cotangent) of a number. The result is expressed in radians.
API DEFINITION

```surql
math::acot(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::acot(1);

-- 0.7853981633974483f
```

##  `math::asin`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathasin)
The `math::asin` function returns the arcsine (inverse sine) of a number, which must be in the range -1 to 1. The result is expressed in radians.
API DEFINITION

```surql
math::asin(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::asin(0.5);

-- 0.5235987755982988f
```

  

##  `math::atan`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathatan)
The `math::atan` function returns the arctangent (inverse tangent) of a number. The result is expressed in radians.
API DEFINITION

```surql
math::atan(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::atan(1);

-- 0.7853981633974483f
```

  

##  `math::bottom`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathbottom)
The `math::bottom` function returns the bottom X set of numbers in an array of numbers.
API DEFINITION

```surql
math::bottom(array<number>, $quantity: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::bottom([1, 2, 3], 2);

-- [2, 1]
```

  

##  `math::ceil`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathceil)
The `math::ceil` function rounds a number up to the next largest whole number.
API DEFINITION

```surql
math::ceil(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::ceil(13.146572);
-- 14f
```

  

##  `math::clamp`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathclamp)
The `math::clamp` function constrains a number within the specified range, defined by a minimum and a maximum value. If the number is less than the minimum, it returns the minimum. If it is greater than the maximum, it returns the maximum.
API DEFINITION

```surql
math::clamp(number, $min: number, $max: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::clamp(1, 5, 10);
-- 5
```

  

##  `math::cos`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathcos)
The `math::cos` function returns the cosine of a number, which is assumed to be in radians. The result is a value between -1 and 1.
API DEFINITION

```surql
math::cos(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::cos(1);
-- 0.5403023058681398f
```

  

##  `math::cot`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathcot)
The `math::cot` function returns the cotangent of a number, which is assumed to be in radians. The cotangent is the reciprocal of the tangent function.
API DEFINITION

```surql
math::cot(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::cot(1);
-- 0.6420926159343308f
```

  

##  `math::deg2rad`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathdeg2rad)
The `math::deg2rad` function converts an angle from degrees to radians.
API DEFINITION

```surql
math::deg2rad(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::deg2rad(180);
-- 3.141592653589793f
```

  

##  `math::e`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathe)
The `math::e` constant represents the base of the natural logarithm (Euler’s number).
API DEFINITION

```surql
math::e -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::e;
-- 2.718281828459045f
```

  

##  `math::fixed`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfixed)
The `math::fixed` function returns a number with the specified number of decimal places.
API DEFINITION

```surql
math::fixed(number, $places: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::fixed(13.146572, 2);

-- 13.15f
```

  

##  `math::floor`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfloor)
The `math::floor` function rounds a number down to the nearest integer.
API DEFINITION

```surql
math::floor(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::floor(13.746189);
-- 13f 
```

  

##  `math::frac_1_pi`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_1_pi)
The `math::frac_1_pi` constant represents the fraction 1/π.
API DEFINITION

```surql
math::frac_1_pi -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_1_pi;

-- 0.3183098861837907f
```

  

##  `math::frac_1_sqrt_2`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_1_sqrt_2)
The `math::frac_1_sqrt_2` constant represents the fraction 1/sqrt(2).
API DEFINITION

```surql
math::frac_1_sqrt_2 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_1_sqrt_2;
-- 0.7071067811865476f
```

  

##  `math::frac_2_pi`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_2_pi)
The `math::frac_2_pi` constant represents the fraction 2/π.
API DEFINITION

```surql
math::frac_2_pi -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_2_pi;
-- 0.6366197723675814f
```

  

##  `math::frac_2_sqrt_pi`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_2_sqrt_pi)
The `math::frac_2_sqrt_pi` constant represents the fraction 2/sqrt(π).
API DEFINITION

```surql
math::frac_2_sqrt_pi -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_2_sqrt_pi;
-- 1.1283791670955126f
```

  

##  `math::frac_pi_2`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_2)
The `math::frac_pi_2` constant represents the fraction π/2.
API DEFINITION

```surql
math::frac_pi_2 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_pi_2;
-- 1.5707963267948966f
```

  

##  `math::frac_pi_3`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_3)
The `math::frac_pi_3` constant represents the fraction π/3.
API DEFINITION

```surql
math::frac_pi_3 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_pi_3;
-- 1.0471975511965979f
```

  

##  `math::frac_pi_4`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_4)
The `math::frac_pi_4` constant represents the fraction π/4.
API DEFINITION

```surql
math::frac_pi_4 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_pi_4;
-- 0.7853981633974483f
```

  

##  `math::frac_pi_6`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_6)
The `math::frac_pi_6` constant represents the fraction π/6.
API DEFINITION

```surql
math::frac_pi_6 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_pi_6;
-- 0.5235987755982989f
```

  

##  `math::frac_pi_8`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathfrac_pi_8)
The `math::frac_pi_8` constant represents the fraction π/8.
API DEFINITION

```surql
math::frac_pi_8 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::frac_pi_8;
-- 0.39269908169872414f
```

  

##  `math::infinity`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathinfinity)
Note
This constant was known as `math::inf` in versions before SurrealDB 3.0.5. The previous path also returns the same value and thus the change to `math::infinity` is not a breaking change.
The `math::infinity` constant represents positive infinity.
API DEFINITION

```surql
math::infinity -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::infinity;

-- Infinity
```

  

##  `math::interquartile`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathinterquartile)
The `math::interquartile` function returns the interquartile of an array of numbers.
API DEFINITION

```surql
math::interquartile(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::interquartile([ 1, 40, 60, 10, 2, 901 ]);
-- 51f
```

  

##  `math::lerp`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlerp)
The `math::lerp` function performs a linear interpolation between two numbers based on a given fraction. The fraction will usually be between 0 and 1, where 0 returns `$num_1` and 1 returns `$num_2`.
API DEFINITION

```surql
math::lerp($num_1: number, $num_2: number, $fraction: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::lerp(0, 10, 0.5);
-- 5f
```

The function will not return an error if the third argument is not in the range of 0 to 1. Instead, it will extrapolate linearly beyond the first two numbers.

```surql
RETURN math::lerp(0, 10, 2);
-- 20
```

  

##  `math::lerpangle`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlerpangle)
The `math::lerpangle` function interpolates between two angles (`$num_1` and `$num_2`) by the given fraction. This is useful for smoothly transitioning between angles.
API DEFINITION

```surql
math::lerpangle($num_1: number, $num_2: number, $fraction: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::lerpangle(0, 180, 0.5);
-- 90f
```

  

##  `math::ln`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathln)
The `math::ln` function returns the natural logarithm (base e) of a number.
API DEFINITION

```surql
math::ln(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::ln(10);
-- 2.302585092994046f
```

  

##  `math::ln_10`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathln_10)
The `math::ln_10` constant represents the natural logarithm (base e) of 10.
API DEFINITION

```surql
math::ln_10 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::ln_10;
-- 2.302585092994046f
```

  

##  `math::ln_2`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathln_2)
The `math::ln_2` constant represents the natural logarithm (base e) of 2.
API DEFINITION

```surql
math::ln_2 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::ln_2;
-- 0.6931471805599453f
```

  

##  `math::log`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog)
The `math::log` function returns the logarithm of a number with a specified base.
API DEFINITION

```surql
math::log(number, $base: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::log(100, 10);
-- 2f
```

  

##  `math::log10`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog10)
The `math::log10` function returns the base-10 logarithm of a number.
API DEFINITION

```surql
math::log10(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::log10(1000);
-- 3f
```

  

##  `math::log10_2`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog10_2)
The `math::log10_2` constant represents the base-10 logarithm of 2.
API DEFINITION

```surql
math::log10_2 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::log10_2;
-- 0.3010299956639812f
```

  

##  `math::log10_e`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog10_e)
The `math::log10_e` constant represents the base-10 logarithm of e, the base of the natural logarithm (Euler’s number).
API DEFINITION

```surql
math::log10_e -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::log10_e;

-- 0.4342944819032518f
```

  

##  `math::log2`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog2)
The `math::log2` function returns the base-2 logarithm of a number.
API DEFINITION

```surql
math::log2(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::log2(8);
-- 3f
```

  

##  `math::log2_10`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog2_10)
The `math::log2_10` constant represents the base-2 logarithm of 10.
API DEFINITION

```surql
math::log2_10 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::log2_10;
-- 3.321928094887362f
```

  

##  `math::log2_e`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathlog2_e)
The `math::log2_e` constant represents the base-2 logarithm of e, the base of the natural logarithm (Euler’s number).
API DEFINITION

```surql
math::log2_e -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::log2_e;
-- 1.4426950408889634f
```

  

##  `math::max`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmax)
The `math::max` function returns the greatest number from an array of numbers.
API DEFINITION

```surql
math::max(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::max([ 26.164, 13.746189, 23, 16.4, 41.42 ]);
-- 41.42f
```

See also:
  * •
[`array::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymax), which extracts the greatest value from an array of values
  * •
[`time::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemax), which extracts the greatest datetime from an array of datetimes

##  `math::mean`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmean)
The `math::mean` function returns the mean of a set of numbers.
API DEFINITION

```surql
math::mean(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::mean([ 26.164, 13.746189, 23, 16.4, 41.42 ]);

-- 24.146037800000002f
```

  

##  `math::median`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmedian)
The `math::median` function returns the median of a set of numbers.
API DEFINITION

```surql
math::median(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::median([ 26.164, 13.746189, 23, 16.4, 41.42 ]);
-- 23f
```

  

##  `math::midhinge`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmidhinge)
The `math::midhinge` function returns the midhinge of an array of numbers.
API DEFINITION

```surql
math::midhinge(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::midhinge([ 1, 40, 60, 10, 2, 901 ]);
-- 29.5f
```

  

##  `math::min`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmin)
The `math::min` function returns the least number from an array of numbers.
API DEFINITION

```surql
math::min(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::min([ 26.164, 13.746189, 23, 16.4, 41.42 ]);
-- 13.746189f
```

See also:
  * •
[`array::min`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymin), which extracts the least value from an array of values
  * •
[`time::min`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemin), which extracts the least datetime from an array of datetimes

##  `math::mode`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmode)
The `math::mode` function returns the value that occurs most often in a set of numbers. In case of a tie, the highest one is returned.
API DEFINITION

```surql
math::mode(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::mode([ 1, 40, 60, 10, 2, 901 ]);
-- 901

RETURN math::mode([ 1, 40, 60, 10, 2, 901, 2 ]);
-- 2
```

  

##  `math::nearestrank`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathnearestrank)
The `math::nearestrank` function returns the nearest rank of an array of numbers by pullinng the closest extant record from the dataset at the %-th percentile.
API DEFINITION

```surql
math::nearestrank(array<number>, $percentile: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::nearestrank([1, 40, 60, 10, 2, 901], 50);
-- 40
```

A number for the percentile outside of the range 0 to 100 will return the output `NaN`.

```surql
-- Nan
math::nearestrank([1, 40, 60, 10, 2, 901], 101);

-- Also Nan
math::nearestrank([1, 40, 60, 10, 2, 901], -1);
```

  

##  `math::neg_infinity`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathneg_infinity)
Note
This constant was known as `math::neg_inf` in versions before SurrealDB 3.0.5. The previous path also returns the same value and thus the change to `math::neg_infinity` is not a breaking change.
The `math::neg_infinity` constant represents negative infinity.
API DEFINITION

```surql
math::neg_infinity -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::neg_infinity;

// -Infinity
```

  

##  `math::percentile`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathpercentile)
The `math::percentile` function returns the value below which a percentage of data falls by getting the N percentile, averaging neighboring records if non-exact.
API DEFINITION

```surql
math::percentile(array<number>, $percentile: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::percentile([1, 40, 60, 10, 2, 901], 50);
-- 25f
```

A number for the percentile outside of the range 0 to 100 will return the output `NaN`.

```surql
-- Nan
math::percentile([1, 40, 60, 10, 2, 901], 101);

-- Also Nan
math::percentile([1, 40, 60, 10, 2, 901], -1);
```

  

##  `math::pi`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathpi)
The `math::pi` constant represents the mathematical constant π.
API DEFINITION

```surql
math::pi -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::pi;
-- 3.141592653589793f
```

  

##  `math::pow`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathpow)
The `math::pow` function returns a number raised to the power of a second number.
API DEFINITION

```surql
math::pow(number, $raise_to: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::pow(1.07, 10);
-- 1.9671513572895665f
```

  

##  `math::product`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathproduct)
The `math::product` function returns the product of a set of numbers.
API DEFINITION

```surql
math::product(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::product([ 26.164, 13.746189, 23, 16.4, 41.42 ]);
-- 5619119.004884841f
```

  

##  `math::rad2deg`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathrad2deg)
The `math::rad2deg` function converts an angle from radians to degrees.
API DEFINITION

```surql
math::rad2deg(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::rad2deg(3.141592653589793);
-- 180f
```

  

##  `math::round`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathround)
The `math::round` function rounds a number up or down to the nearest integer.
API DEFINITION

```surql
math::round(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::round(13.53124);
-- 14f
```

  

##  `math::sign`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsign)
The `math::sign` function returns the sign of a number, indicating whether the number is positive, negative, or zero.  
It returns 1 for positive numbers, -1 for negative numbers, and 0 for zero.
API DEFINITION

```surql
math::sign(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::sign(-42);
-- -1
```

  

##  `math::sin`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsin)
The `math::sin` function returns the sine of a number, which is assumed to be in radians.
API DEFINITION

```surql
math::sin(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::sin(1);
-- 0.8414709848078965f
```

  

##  `math::spread`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathspread)
The `math::spread` function returns the spread of an array of numbers.
API DEFINITION

```surql
math::spread(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::spread([ 1, 40, 60, 10, 2, 901 ]);
-- 900
```

  

##  `math::sqrt`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsqrt)
The `math::sqrt` function returns the square root of a number.
API DEFINITION

```surql
math::sqrt(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::sqrt(15);
-- 3.872983346207417f
```

  

##  `math::sqrt_2`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsqrt_2)
The `math::sqrt_2` constant represents the square root of 2.
API DEFINITION

```surql
math::sqrt_2 -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::sqrt_2;
-- 1.4142135623730951f
```

  

##  `math::stddev`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathstddev)
The `math::stddev` function calculates how far a set of numbers are away from the mean.
API DEFINITION

```surql
math::stddev(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::stddev([ 1, 40, 60, 10, 2, 901 ]);
-- 359.37167389765153f
```

As of SurrealDB 3.0.0, this function can be used [inside a table view](https://surrealdb.com/docs/reference/query-language/statements/select#mathstddev-and-mathvariance-in-table-views).

```surql
DEFINE TABLE person SCHEMALESS;
DEFINE TABLE person_stats AS
	SELECT
		count(),
		age,
		math::stddev(score) AS score_stddev
	FROM person
	GROUP BY age;
```

  

##  `math::sum`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsum)
The `math::sum` function returns the total sum of a set of numbers.
API DEFINITION

```surql
math::sum(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::sum([ 26.164, 13.746189, 23, 16.4, 41.42 ]);

-- 120.730189
```

This function on its own expects a numeric value at each point in an array, meaning that on its own it will not be able to be used on an array that contains `NONE` or `NULL` values.

```surql
math::sum([0, NONE, 10dec, 10.7, NULL]);

-- Error: Incorrect arguments for function math::sum().
-- Argument 1 was the wrong type.
-- Expected `number` but found `NONE` when coercing an element of `array<number>`
```

However, `NONE` and `NULL` can be coalesced into a default value by using the `??` operator (the "null coalescing operator").

```surql
NONE ?? 0; -- Finds NONE so returns latter value: 0
1000 ?? 0; -- Finds 1000 so returns 1000 instead of 0
```

Inside an array the [`array::map()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymap) function can be used to ensure that each value is the number 0 if a `NONE` or `NULL` is encountered.
Classic [array filtering](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/arrays#mapping-and-filtering-on-arrays) can also be used to simply remove any `NONE` or `NULL` values before `math::sum()` is called.

```surql
// Classic array filtering, removes NONE / NULL
[0,NONE,10dec,10.7,NULL][? $this];
// array::map() function, turns NONE / NULL to 0
[0, NONE, 10dec, 10.7, NULL].map(|$num| $num ?? 0);
```

With this mapping in place, `math::sum()` will be guaranteed to work.

```surql
// Classic array filtering
math::sum([0,NONE,10dec,10.7,NULL][? $this]);
// array::map() function
math::sum([0, NONE, 10dec, 10.7, NULL].map(|$num| $num ?? 0));

-- 20.7dec
```

  

##  `math::tan`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtan)
The `math::tan` function returns the tangent of a number, which is assumed to be in radians.
API DEFINITION

```surql
math::tan(number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::tan(1);
-- 1.557407724654902f
```

  

##  `math::tau`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtau)
The `math::tau` constant represents the mathematical constant τ, which is equal to 2π.
API DEFINITION

```surql
math::tau -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::tau;
-- 6.283185307179586f
```

  

##  `math::top`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtop)
The `math::top` function returns the top of an array of numbers.
API DEFINITION

```surql
math::top(array<number>, $quantity: number) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::top([1, 40, 60, 10, 2, 901], 3);
-- [40, 901, 60]
```

  

##  `math::trimean`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathtrimean)
The `math::trimean` function returns the trimean of an array of numbers.
API DEFINITION

```surql
math::trimean(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::trimean([ 1, 40, 60, 10, 2, 901 ]);
-- 27.25f
```

  

##  `math::variance`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathvariance)
The `math::variance` function returns the variance of an array of numbers.
API DEFINITION

```surql
math::variance(array<number>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN math::variance([ 1, 40, 60, 10, 2, 901 ]);
-- 129148
```

As of SurrealDB 3.0.0, this function can be used [inside a table view](https://surrealdb.com/docs/reference/query-language/statements/select#mathstddev-and-mathvariance-in-table-views).

```surql
DEFINE TABLE person SCHEMALESS;
DEFINE TABLE person_stats AS
	SELECT
		count(),
		age,
		math::variance(score) AS score_variance
	FROM person
	GROUP BY age;
```
