# Visitor Workflow

Each visitor has one extraction responsibility.

| Visitor | Responsibility |
| --- | --- |
| `FunctionVisitor` | Function signatures, decorators, docstrings, local variables, recursion signal |
| `ClassVisitor` | Class declarations, inheritance, methods, class variables |
| `ImportVisitor` | Import statements and import classification |
| `LoopVisitor` | Loop structure and loop-contained syntax signals |
| `CallVisitor` | Call sites plus file/network operation extraction |
| `AsyncVisitor` | Async syntax |
| `ExceptionVisitor` | Exception syntax and custom exception declarations |
| `SymbolVisitor` | Scope hierarchy, definitions, assignments, references |
| `MetadataVisitor` | Node location, parent, scope, depth, AST node type |
| `CFGVisitor` | Lightweight control-flow nodes and edges |

Visitors should stay syntactic. Future interpretation belongs in separate research modules.
