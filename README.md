# htcw_buffers

htcw_buffers is a code generator that generates code to serialize and deserialize simple fixed size structures.

It allows you to define your interface as a C header file, accepting a fair subset of C, including structs and enums.

The structs can reference other structs in the file and can contain fixed size arrays and fixed size strings.

The generated C code is fast, zero allocation, and flexible, allowing you to stream from and to arbitrary sources using custom callbacks

The generated C# code is fairly efficient, but does allocate, leveraging the GC in order to give you a cleanly typed API. It also renames the definitions to follow dotnet naming guidelines, so `ip_address` becaomes `IPAddress`.

You'll need python installed to run the scripts.

Any shared code can be produced by the scripts so you don't need to reference any runtimes.

## Generating C code
Options:
- `--buffers` generate shared code
- `--out <dir>` override the output directory

```
python .\buffers_gen_c.py --buffers example.h
```

## C# code
Options:
- `--buffers` generate shared code
- `--namespace <namespace>` generate under the indicated namespace
- `--out <dir>` override the output directory

```
python .\buffers_gen_cs.py --namespace Example --buffers example.h
```