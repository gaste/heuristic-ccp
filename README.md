# Combined Configuration Problem (CCP) Heuristic
The "A2 alternate ordering" heuristic designed by
[Benni](https://github.com/Yarrick13), implemented using the Python heuristic
interface of [WASP]().

## Usage
Use the heuristic together with [HWASP](https://github.com/Yarrick13/hwasp)
on the heuristic branch. To run the heuristic on the sample instance, execute
```
gringo ccp-encoding.asp ccp-sample-instance.asp | hwasp --heuristic-interpreter=python --heuristic-scriptname=heuristic
```