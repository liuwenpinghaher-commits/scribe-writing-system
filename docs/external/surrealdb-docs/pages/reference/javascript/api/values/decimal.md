---
title: "https://surrealdb.com/docs/reference/javascript/api/values/decimal"
url: "https://surrealdb.com/docs/reference/javascript/api/values/decimal"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/decimal

Source: https://surrealdb.com/docs/reference/javascript/api/values/decimal

The `Decimal` class provides arbitrary precision decimal numbers, essential for financial calculations and applications where floating-point precision errors are unacceptable.
**Import:**

```ts
import { Decimal } from 'surrealdb';
```

**Source:** [value/decimal.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/decimal.ts)
##  Why use Decimal?[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#why-use-decimal)
JavaScript's `number` type uses floating-point arithmetic, which can lead to precision errors:

```ts
// Floating-point precision error
console.log(0.1 + 0.2); // 0.30000000000000004

// Decimal preserves precision
const a = new Decimal('0.1');
const b = new Decimal('0.2');
console.log(a.add(b).toString()); // '0.3'
```

##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#constructor)
###  `new Decimal(value)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#constructor)
Create a new arbitrary precision decimal.
Syntax

```ts
new Decimal(decimal) // Clone existing
new Decimal(string) // Parse from string
new Decimal(number | bigint) // From number
new Decimal([int, frac, scale]) // From tuple
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `value`  | `Decimal | string | number | bigint | [bigint, bigint, number]`  | Value to create decimal from.  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#examples)

```ts
// From string (recommended for precision)
const price = new Decimal('19.99');
const precise = new Decimal('0.123456789012345678901234567890');

// From number (may have floating-point precision)
const value = new Decimal(19.99);

// From bigint
const large = new Decimal(1000000n);

// Scientific notation
const scientific = new Decimal('1.23e-10');

// Clone existing
const copy = new Decimal(price);
```

##  Static methods[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#static-methods)
###  `Decimal.fromScientificNotation(input)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#fromscientificnotation)
Parse a decimal from scientific notation string.
Syntax

```ts
Decimal.fromScientificNotation(input)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `input`  | `string`  | Scientific notation string to parse.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns)
`Decimal` - Parsed decimal
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example)

```ts
const value = Decimal.fromScientificNotation('1.23e10');
const small = Decimal.fromScientificNotation('5.67e-8');
```

##  Properties[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#properties)
###  `.int`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#int)
The integer part of the decimal as a `bigint`.

```ts
const d = new Decimal('19.99');
console.log(d.int); // 19n
```

* * *
###  `.frac`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#frac)
The fractional part of the decimal as a `bigint`.

```ts
const d = new Decimal('19.99');
console.log(d.frac); // 99n
```

* * *
###  `.scale`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#scale)
The number of decimal places.

```ts
const d = new Decimal('19.99');
console.log(d.scale); // 2
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#instance-methods)
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#tostring)
Convert to string representation (preserves precision).
Syntax

```ts
decimal.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-1)
`string` - String representation
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-1)

```ts
const price = new Decimal('19.99');
console.log(price.toString()); // '19.99'

const precise = new Decimal('0.123456789012345678901234567890');
console.log(precise.toString()); // Full precision preserved
```

* * *
###  `.toFloat()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#tofloat)
Convert to JavaScript number.
Syntax

```ts
decimal.toFloat()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-2)
`number` - JavaScript number (may lose precision)
Warning
Converting to number may lose precision for very large or very precise values.
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-2)

```ts
const price = new Decimal('19.99');
const num = price.toFloat(); // 19.99

// Precision loss example
const precise = new Decimal('0.123456789012345678901234567890');
const lost = precise.toFloat(); // Precision beyond ~15 digits is lost
```

* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#tojson)
Serialize for JSON.
Syntax

```ts
decimal.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-3)
`string` - String representation for JSON
* * *
###  `.toBigInt()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#tobigint)
Truncate to a `bigint`, discarding the fractional part.
Syntax

```ts
decimal.toBigInt()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-4)
`bigint` - Integer part of the decimal
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-3)

```ts
const d = new Decimal('19.99');
console.log(d.toBigInt()); // 19n
```

* * *
###  `.toFixed(precision)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#tofixed)
Format the decimal with a fixed number of decimal places.
Syntax

```ts
decimal.toFixed(precision)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `precision`  | `number`  | Number of decimal places.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-5)
`string` - Fixed-point notation string
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-4)

```ts
const d = new Decimal('19.9');
console.log(d.toFixed(4)); // '19.9000'
```

* * *
###  `.toScientific()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#toscientific)
Convert to scientific notation string.
Syntax

```ts
decimal.toScientific()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-6)
`string` - Scientific notation representation
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-5)

```ts
const d = new Decimal('12300');
console.log(d.toScientific()); // e.g. '1.23e4'
```

* * *
###  `.toParts()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#toparts)
Decompose the decimal into its constituent parts.
Syntax

```ts
decimal.toParts()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-7)
`{ int: bigint, frac: bigint, scale: number }` - The integer part, fractional part, and scale
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-6)

```ts
const d = new Decimal('19.99');
const parts = d.toParts();
// { int: 19n, frac: 99n, scale: 2 }
```

* * *
###  `.add(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#add)
Add another decimal.
Syntax

```ts
decimal.add(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Decimal`  | Value to add.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-8)
`Decimal` - Sum
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-7)

```ts
const price1 = new Decimal('19.99');
const price2 = new Decimal('5.50');
const total = price1.add(price2);
console.log(total.toString()); // '25.49'
```

* * *
###  `.sub(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#sub)
Subtract another decimal.
Syntax

```ts
decimal.sub(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Decimal`  | Value to subtract.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-9)
`Decimal` - Difference
* * *
###  `.mul(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#mul)
Multiply by another decimal.
Syntax

```ts
decimal.mul(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Decimal`  | Value to multiply by.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-10)
`Decimal` - Product
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-8)

```ts
const price = new Decimal('19.99');
const quantity = new Decimal('3');
const total = price.mul(quantity);
console.log(total.toString()); // '59.97'
```

* * *
###  `.div(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#div)
Divide by another decimal.
Syntax

```ts
decimal.div(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Decimal`  | Value to divide by.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-11)
`Decimal` - Quotient
* * *
###  `.mod(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#mod)
Calculate the remainder after division.
Syntax

```ts
decimal.mod(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-7)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Decimal`  | Divisor.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-12)
`Decimal` - Remainder
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-9)

```ts
const d = new Decimal('10');
const remainder = d.mod(new Decimal('3'));
console.log(remainder.toString()); // '1'
```

* * *
###  `.abs()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#abs)
Get the absolute value.
Syntax

```ts
decimal.abs()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-13)
`Decimal` - Absolute value
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-10)

```ts
const d = new Decimal('-19.99');
console.log(d.abs().toString()); // '19.99'
```

* * *
###  `.neg()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#neg)
Negate the decimal.
Syntax

```ts
decimal.neg()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-14)
`Decimal` - Negated value
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-11)

```ts
const d = new Decimal('19.99');
console.log(d.neg().toString()); // '-19.99'
```

* * *
###  `.round(precision)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#round)
Round to a given number of decimal places.
Syntax

```ts
decimal.round(precision)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-8)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `precision`  | `number`  | Number of decimal places to round to.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-15)
`Decimal` - Rounded value
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-12)

```ts
const d = new Decimal('19.995');
console.log(d.round(2).toString()); // '20.00'
```

* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#equals)
Check if two decimals are equal.
Syntax

```ts
decimal.equals(other)
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-16)
`boolean` - True if equal
* * *
###  `.compare(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#compare)
Compare two decimals.
Syntax

```ts
decimal.compare(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#parameters-9)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Decimal`  | Decimal to compare against.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-17)
`number` - Returns `-1` if less than, `0` if equal, `1` if greater than
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-13)

```ts
const a = new Decimal('10');
const b = new Decimal('20');
console.log(a.compare(b)); // -1
console.log(b.compare(a)); // 1
console.log(a.compare(a)); // 0
```

* * *
###  `.isZero()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#iszero)
Check if the decimal is zero.
Syntax

```ts
decimal.isZero()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-18)
`boolean` - True if the value is zero
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-14)

```ts
const zero = new Decimal('0');
console.log(zero.isZero()); // true

const nonZero = new Decimal('1');
console.log(nonZero.isZero()); // false
```

* * *
###  `.isNegative()`[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#isnegative)
Check if the decimal is negative.
Syntax

```ts
decimal.isNegative()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#returns-19)
`boolean` - True if the value is negative
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#example-15)

```ts
const neg = new Decimal('-5');
console.log(neg.isNegative()); // true

const pos = new Decimal('5');
console.log(pos.isNegative()); // false
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#complete-examples)
###  Financial calculations[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#financial-calculations)

```ts
import { Surreal, Decimal, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Product prices
const product = await db.create(new Table('products')).content({
    name: 'Widget',
    price: new Decimal('19.99'),
    tax_rate: new Decimal('0.075') // 7.5%
});

// Calculate total with tax
const price = new Decimal(product.price);
const taxRate = new Decimal(product.tax_rate);
const tax = price.mul(taxRate);
const total = price.add(tax);

console.log('Price:', price.toString());     // 19.99
console.log('Tax:', tax.toString());         // 1.49925
console.log('Total:', total.toString());     // 21.48925
```

###  Order total calculation[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#order-total-calculation)

```ts
interface OrderItem {
    product: string;
    price: Decimal;
    quantity: number;
}

function calculateOrderTotal(items: OrderItem[]): Decimal {
    let total = new Decimal('0');
    
    for (const item of items) {
        const itemTotal = item.price.mul(new Decimal(item.quantity));
        total = total.add(itemTotal);
    }
    
    return total;
}

const items = [
    { product: 'Widget', price: new Decimal('19.99'), quantity: 2 },
    { product: 'Gadget', price: new Decimal('29.99'), quantity: 1 },
    { product: 'Tool', price: new Decimal('9.99'), quantity: 3 }
];

const orderTotal = calculateOrderTotal(items);
console.log('Order total:', orderTotal.toString()); // '99.94'
```

###  Currency exchange[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#currency-exchange)

```ts
// Exchange rate calculation
const usdAmount = new Decimal('100.00');
const exchangeRate = new Decimal('1.18'); // USD to EUR

const eurAmount = usdAmount.mul(exchangeRate);
console.log(`$${usdAmount} = €${eurAmount}`);
```

###  Interest calculation[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#interest-calculation)

```ts
// Calculate compound interest
function calculateCompoundInterest(
    principal: Decimal,
    rate: Decimal,
    periods: number
): Decimal {
    let amount = principal;
    const onePlusRate = new Decimal('1').add(rate);
    
    for (let i = 0; i < periods; i++) {
        amount = amount.mul(onePlusRate);
    }
    
    return amount;
}

const principal = new Decimal('1000.00');
const annualRate = new Decimal('0.05'); // 5%
const years = 10;

const finalAmount = calculateCompoundInterest(principal, annualRate, years);
console.log('Final amount:', finalAmount.toString());
```

###  Database storage[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#database-storage)

```ts
// Store precise financial data
const transaction = await db.create(new Table('transactions')).content({
    user: userId,
    amount: new Decimal('149.99'),
    fee: new Decimal('2.50'),
    tax: new Decimal('11.25'),
    timestamp: DateTime.now()
});

// Query and calculate
const transactions = await db.select(new Table('transactions'));
let totalAmount = new Decimal('0');

for (const txn of transactions) {
    totalAmount = totalAmount.add(txn.amount);
}

console.log('Total:', totalAmount.toString());
```

###  Percentage calculations[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#percentage-calculations)

```ts
// Calculate percentage
function calculatePercentage(value: Decimal, percentage: Decimal): Decimal {
    return value.mul(percentage).div(new Decimal('100'));
}

const price = new Decimal('100.00');
const discount = new Decimal('15'); // 15%

const discountAmount = calculatePercentage(price, discount);
const finalPrice = price.sub(discountAmount);

console.log('Discount:', discountAmount.toString()); // '15.00'
console.log('Final price:', finalPrice.toString()); // '85.00'
```

###  Scientific calculations[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#scientific-calculations)

```ts
// High precision scientific value
const avogadroNumber = new Decimal('6.02214076e23');
const boltzmannConstant = new Decimal('1.380649e-23');

console.log('Avogadro:', avogadroNumber.toString());
console.log('Boltzmann:', boltzmannConstant.toString());
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#best-practices)
###  1. Use strings for input[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#1-use-strings-for-input)

```ts
// Good: String input preserves precision
const price = new Decimal('19.99');

// Caution: Number input may have floating-point errors
const price = new Decimal(19.99); // Already has float imprecision
```

###  2. Keep as Decimal for calculations[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#2-keep-as-decimal-for-calculations)

```ts
// Good: All calculations use Decimal
const subtotal = price.mul(quantity);
const tax = subtotal.mul(taxRate);
const total = subtotal.add(tax);

// Avoid: Converting to number mid-calculation
const subtotal = price.toFloat() * quantity; // Loses precision
```

###  3. Convert to string for display[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#3-convert-to-string-for-display)

```ts
// Good: String preserves precision
const display = price.toString();
console.log(`$${display}`);

// Avoid: Number may lose precision
const display = price.toFloat().toFixed(2);
```

###  4. Store decimals in database[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#4-store-decimals-in-database)

```ts
// Good: Store as Decimal
await db.create(table).content({
    price: new Decimal('19.99')
});

// Avoid: Store as number
await db.create(table).content({
    price: 19.99 // Float imprecision
});
```

##  Common pitfalls[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#common-pitfalls)
###  Floating-point input[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#floating-point-input)

```ts
// Problem: Number already has floating-point error
const wrong = new Decimal(0.1 + 0.2); // 0.30000000000000004

// Solution: Use string input
const correct = new Decimal('0.1').add(new Decimal('0.2')); // 0.3
```

###  Premature conversion to number[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#premature-conversion-to-number)

```ts
// Problem: Loses precision
const result = price.toFloat() + tax.toFloat();

// Solution: Keep as Decimal
const result = price.add(tax);
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/decimal#see-also)
  * •
[Data types overview](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Using Decimal in queries
  * •
[SurrealQL decimal](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers) - Database decimal type
