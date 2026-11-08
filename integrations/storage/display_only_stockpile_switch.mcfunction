execute if block ~ ~ ~ create:stockpile_switch run data merge block ~ ~ ~ {OnAboveAmount:1.0f,OffBelowAmount:0.0f,Inverted:1b,InStacks:0b}
execute if block ~ ~ ~ create:stockpile_switch if data block ~ ~ ~ {CurrentAmount:0} run data merge block ~ ~ ~ {Powered:1b}
execute if block ~ ~ ~ create:stockpile_switch unless data block ~ ~ ~ {CurrentAmount:0} run data merge block ~ ~ ~ {Powered:0b}
