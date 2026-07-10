---
title: "https://surrealdb.com/docs/reference/javascript/api/values/table"
url: "https://surrealdb.com/docs/reference/javascript/api/values/table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/table

Source: https://surrealdb.com/docs/reference/javascript/api/values/table

The `Table` class provides type-safe references to database tables, enabling TypeScript type checking for query results.
**Import:**

```ts
import { Table } from 'surrealdb';
```

**Source:** [value/table.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/table.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/values/table#type-parameters)
  * •
`T` - The record type for this table (optional, defaults to `string`)

##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/table#constructor)
###  `new Table<T>(name)`[](https://surrealdb.com/docs/reference/javascript/api/values/table#constructor)
Create a new table reference.
Syntax

```ts
new Table(name)
new Table<RecordType>(name)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/table#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  | The table name.  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/table#examples)

```ts
// Basic table reference
const users = new Table('users');

// Type-safe table reference
interface User {
    id: RecordId;
    name: string;
    email: string;
}

const users = new Table<User>('users');

// TypeScript now knows the result type
const allUsers: User[] = await db.select(users);
```

##  Properties[](https://surrealdb.com/docs/reference/javascript/api/values/table#properties)
###  `name`[](https://surrealdb.com/docs/reference/javascript/api/values/table#name)
The table name.
**Type:** `string`

```ts
const users = new Table('users');
console.log(users.name); // 'users'
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/table#instance-methods)
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/table#tostring)
Convert to string representation (escaped table name).
Syntax

```ts
table.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/table#returns)
`string` - Escaped table name
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/table#example)

```ts
const users = new Table('users');
console.log(users.toString()); // 'users'

// Handles special characters
const special = new Table('my-table');
console.log(special.toString()); // Properly escaped
```

* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/table#tojson)
Serialize for JSON.
Syntax

```ts
table.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/table#returns-1)
`string` - Table name
* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/table#equals)
Check if two table references are equal.
Syntax

```ts
table.equals(other)
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/table#returns-2)
`boolean` - True if equal
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/values/table#complete-examples)
###  Type-safe queries[](https://surrealdb.com/docs/reference/javascript/api/values/table#type-safe-queries)

```ts
import { Surreal, Table } from 'surrealdb';

// Define your data model
interface User {
    id: RecordId;
    name: string;
    email: string;
    age: number;
}

interface Post {
    id: RecordId;
    title: string;
    content: string;
    author: RecordId;
}

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Create type-safe table references
const users = new Table<User>('users');
const posts = new Table<Post>('posts');

// TypeScript knows the return types
const allUsers: User[] = await db.select(users);
const allPosts: Post[] = await db.select(posts);

// Type checking in IDE
allUsers[0].name; // ✓ TypeScript knows this exists
allUsers[0].title; // ✗ TypeScript error: Property 'title' does not exist
```

###  Select operations[](https://surrealdb.com/docs/reference/javascript/api/values/table#select-operations)

```ts
const users = new Table<User>('users');

// Select all records
const all = await db.select(users);

// Select with filtering
const active = await db.select(users)
    .where('active = true');

// Select with pagination
const page = await db.select(users)
    .limit(10)
    .start(0);
```

###  Create operations[](https://surrealdb.com/docs/reference/javascript/api/values/table#create-operations)

```ts
const users = new Table<User>('users');

// Create single record with auto-generated ID
const user = await db.create(users).content({
    name: 'John Doe',
    email: 'john@example.com',
    age: 30
});

// Create multiple records
const newUsers = await db.insert(users, [
    { name: 'Alice', email: 'alice@example.com', age: 25 },
    { name: 'Bob', email: 'bob@example.com', age: 35 }
]);
```

###  Update operations[](https://surrealdb.com/docs/reference/javascript/api/values/table#update-operations)

```ts
const users = new Table<User>('users');

// Update all records in table
const updated = await db.update(users)
    .merge({ verified: true })
    .where('email_confirmed = true');

// Update with content
await db.update(users)
    .content({
        name: 'New Name',
        email: 'new@example.com',
        age: 31
    })
    .where('id = users:john');
```

###  Delete operations[](https://surrealdb.com/docs/reference/javascript/api/values/table#delete-operations)

```ts
const users = new Table<User>('users');

// Delete all inactive users
const deleted = await db.delete(users)
    .where('inactive = true');

// Get deleted records
const deletedWithData = await db.delete(users)
    .output('BEFORE')
    .where('created_at < $date', { 
        date: DateTime.parse('2024-01-01') 
    });
```

###  Multiple tables[](https://surrealdb.com/docs/reference/javascript/api/values/table#multiple-tables)

```ts
interface Product {
    id: RecordId;
    name: string;
    price: Decimal;
}

interface Order {
    id: RecordId;
    user: RecordId;
    products: RecordId[];
    total: Decimal;
}

const products = new Table<Product>('products');
const orders = new Table<Order>('orders');
const users = new Table<User>('users');

// Work with multiple tables
const [allProducts, allOrders, allUsers] = await Promise.all([
    db.select(products),
    db.select(orders),
    db.select(users)
]);
```

###  Query builder pattern[](https://surrealdb.com/docs/reference/javascript/api/values/table#query-builder-pattern)

```ts
const users = new Table<User>('users');

// Build complex queries
const query = db.select(users)
    .fields('name', 'email', 'age')
    .where('age >= $minAge', { minAge: 18 })
    .order('name ASC')
    .limit(100);

const results = await query;
```

###  Live queries[](https://surrealdb.com/docs/reference/javascript/api/values/table#live-queries)

```ts
const users = new Table<User>('users');

// Subscribe to table changes
const subscription = await db.live(users);

for await (const update of subscription) {
    if (update.action === 'CREATE') {
        console.log('New user:', update.result);
    } else if (update.action === 'UPDATE') {
        console.log('User updated:', update.result);
    } else if (update.action === 'DELETE') {
        console.log('User deleted:', update.result);
    }
}

// Clean up
await subscription.kill();
```

###  Transactions[](https://surrealdb.com/docs/reference/javascript/api/values/table#transactions)

```ts
const users = new Table<User>('users');
const orders = new Table<Order>('orders');

const txn = await db.beginTransaction();

try {
    // Create user
    const user = await txn.create(users).content({
        name: 'Jane Doe',
        email: 'jane@example.com'
    });
    
    // Create order
    await txn.create(orders).content({
        user: user.id,
        products: [],
        total: new Decimal('0')
    });
    
    await txn.commit();
} catch (error) {
    await txn.cancel();
}
```

###  Generic table functions[](https://surrealdb.com/docs/reference/javascript/api/values/table#generic-table-functions)

```ts
// Create reusable functions
async function getAllFromTable<T>(
    db: Surreal,
    table: Table<T>
): Promise<T[]> {
    return db.select(table);
}

async function deleteAllFromTable<T>(
    db: Surreal,
    table: Table<T>
): Promise<T[]> {
    return db.delete(table);
}

// Use with any table
const users = await getAllFromTable(db, new Table<User>('users'));
const posts = await getAllFromTable(db, new Table<Post>('posts'));
```

###  Table schema validation[](https://surrealdb.com/docs/reference/javascript/api/values/table#table-schema-validation)

```ts
// Define table with strict types
interface StrictUser {
    id: RecordId<'users', string>;
    name: string;
    email: string;
    age: number;
    created_at: DateTime;
    updated_at: DateTime;
}

const users = new Table<StrictUser>('users');

// TypeScript enforces the schema
const user = await db.create(users).content({
    name: 'Alice',
    email: 'alice@example.com',
    age: 25,
    created_at: DateTime.now(),
    updated_at: DateTime.now()
    // Missing fields or wrong types will cause TypeScript errors
});
```

###  Repository pattern[](https://surrealdb.com/docs/reference/javascript/api/values/table#repository-pattern)

```ts
class UserRepository {
    private table = new Table<User>('users');
    
    constructor(private db: Surreal) {}
    
    async getAll(): Promise<User[]> {
        return this.db.select(this.table);
    }
    
    async getById(id: RecordId): Promise<User | undefined> {
        return this.db.select(id);
    }
    
    async create(data: Omit<User, 'id'>): Promise<User> {
        return this.db.create(this.table).content(data);
    }
    
    async update(id: RecordId, data: Partial<User>): Promise<User> {
        return this.db.update(id).merge(data);
    }
    
    async delete(id: RecordId): Promise<void> {
        await this.db.delete(id);
    }
    
    async findByEmail(email: string): Promise<User[]> {
        return this.db.select(this.table)
            .where('email = $email', { email });
    }
}

// Usage
const userRepo = new UserRepository(db);
const users = await userRepo.getAll();
const john = await userRepo.findByEmail('john@example.com');
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/values/table#best-practices)
###  1. Use type parameters[](https://surrealdb.com/docs/reference/javascript/api/values/table#1-use-type-parameters)

```ts
// Good: Type-safe
const users = new Table<User>('users');
const results: User[] = await db.select(users);

// Avoid: No type safety
const users = new Table('users');
const results = await db.select(users); // any[]
```

###  2. Define interfaces for tables[](https://surrealdb.com/docs/reference/javascript/api/values/table#2-define-interfaces-for-tables)

```ts
// Good: Clear data structure
interface User {
    id: RecordId;
    name: string;
    email: string;
    created_at: DateTime;
}

const users = new Table<User>('users');

// Avoid: Using 'any' or no interface
const users = new Table('users');
```

###  3. Reuse table references[](https://surrealdb.com/docs/reference/javascript/api/values/table#3-reuse-table-references)

```ts
// Good: Single source of truth
const USERS_TABLE = new Table<User>('users');

async function getUsers() {
    return db.select(USERS_TABLE);
}

async function createUser(data: Omit<User, 'id'>) {
    return db.create(USERS_TABLE).content(data);
}

// Avoid: Creating new references everywhere
async function getUsers() {
    return db.select(new Table('users'));
}
```

###  4. Use with recordId for type safety[](https://surrealdb.com/docs/reference/javascript/api/values/table#4-use-with-recordid-for-type-safety)

```ts
// Good: Strongly typed
interface User {
    id: RecordId<'users', string>;
    name: string;
}

const users = new Table<User>('users');

// TypeScript ensures correct table name
const userId: RecordId<'users', string> = new RecordId('users', 'john');
```

##  Common patterns[](https://surrealdb.com/docs/reference/javascript/api/values/table#common-patterns)
###  Enum-based tables[](https://surrealdb.com/docs/reference/javascript/api/values/table#enum-based-tables)

```ts
enum Tables {
    Users = 'users',
    Posts = 'posts',
    Comments = 'comments'
}

const users = new Table<User>(Tables.Users);
const posts = new Table<Post>(Tables.Posts);
```

###  Table factory[](https://surrealdb.com/docs/reference/javascript/api/values/table#table-factory)

```ts
function createTable<T>(name: string): Table<T> {
    return new Table<T>(name);
}

const users = createTable<User>('users');
const posts = createTable<Post>('posts');
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/table#see-also)
  * •
[RecordId](https://surrealdb.com/docs/reference/javascript/api/values/record-id) - Record identifiers
  * •
[Data types overview](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Using Table in queries
  * •
[SurrealQL tables](https://surrealdb.com/docs/reference/query-language/statements/define/table) - Database table definitions
