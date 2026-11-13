# Power Grid diagnostics

An operator can inspect Power Grid measurements within six blocks of a command position:

```mcfunction
execute positioned <x> <y> <z> run kubejs custom_command expedition_powergrid_probe
```

The server log receives one `[PG-PROBE]` JSON record containing terminal voltages, solver convergence, generator power and current, winding current and magnetic-field bounds. The command reads Power Grid components and does not change world state or inspect unrelated inventories. Power Grid is optional; the command does nothing when that mod is absent.

Validation:

```sh
node tools/powergrid-diagnostics/test.cjs
```
