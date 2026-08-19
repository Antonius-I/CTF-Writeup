# HackTheBox Writeup: It's Oops PM (Hardware)

## Introduction

This challenge is titled **"It's Oops PM"**, part of the hardware category, worth 850 points. According to the scenario, the team discovers an environmental sensor that communicates with a satellite through a crypto-processor. After hand-drawing the diagrams and emulating the chip's logic in VHDL, they uncover what appears to be a backdoor embedded in the logic, which only triggers under a specific input. My task was to analyze that logic, find a way to trigger the backdoor, and then connect to the satellite to retrieve the flag.

![](Description.png)

## Preparation

I started by downloading the scenario files provided through the **Scenario Files** button. After extracting the archive, the following five files were included:

```
hardware_its_oops_pm/
├── key.vhdl
├── encryption.vhdl
├── tpm.vhdl
├── backdoor.vhdl
└── schematic.png
```

[IMAGE: unzip result / folder listing of scenario files — remove after replacing]

I also obtained the address and port needed to connect to the satellite via the **Spawn Docker** button:

```
nc 154.57.164.77 31117
```

[IMAGE: spawn docker view showing IP and port — remove after replacing]

## Schematic Analysis

Before diving into the VHDL code line by line, I first looked at the block diagram in `schematic.png` to get a general understanding of the data flow.

[IMAGE: schematic.png — remove after replacing]

The diagram shows four main blocks:

- **Input** — receives the incoming data
- **Key** — generates the internal key
- **Crypto** — encrypts the data using the key
- **Logic** — processes the input to produce a control signal
- **Mux** — selects the final output based on the signal from the Logic block, choosing between the encrypted data or an alternate path

This pattern hints at a possible alternate (bypass) path on the final output, controlled by the Logic block — this is what I needed to trace further in the VHDL source.

## VHDL Source Analysis

### 1. key.vhdl

```vhdl
entity ckey is
    Port (
        K : out STD_LOGIC_VECTOR(15 downto 0)
    );
end ckey;

architecture Behavioral of ckey is
    constant key : STD_LOGIC_VECTOR(15 downto 0) := "0110001111100001";
begin
    K <= key;
end Behavioral;
```

This module is straightforward — it simply outputs a hardcoded 16-bit constant as the internal key:

```
Key = 0110001111100001
```

[IMAGE: contents of key.vhdl in editor/terminal — remove after replacing]

### 2. encryption.vhdl

```vhdl
entity encryption is
    Port (
        D, K : in STD_LOGIC_VECTOR(15 downto 0);
        E : out STD_LOGIC_VECTOR(15 downto 0)
    );
end encryption;

architecture Behavioral of encryption is
begin
    process(D, K)
    begin
        for i in 1 to 15 loop
            E(i) <= D(i) XOR K(i);
        end loop;

        E(0) <= NOT K(0);
        E(6) <= NOT K(6);
        E(13) <= NOT K(13);
    end process;
end Behavioral;
```

This module takes the data (`D`) and the key (`K`), then XORs each bit from index 1 to 15. Bits 0, 6, and 13 are handled differently — their value is the negation (`NOT`) of the corresponding key bit, rather than an XOR with the data. This is the chip's main encryption routine.

[IMAGE: contents of encryption.vhdl in editor/terminal — remove after replacing]

### 3. backdoor.vhdl

```vhdl
entity backdoor is
    Port (
        D : in STD_LOGIC_VECTOR(15 downto 0);
        B : out STD_LOGIC
    );
end backdoor;

architecture Behavioral of backdoor is
    constant pattern : STD_LOGIC_VECTOR(15 downto 0) := "1111111111101001";
begin
    process(D)
    begin
        if D = pattern then
            B <= '1';
        else
            B <= '0';
        end if;
    end process;
end Behavioral;
```

This is the most important part. This module compares the input data (`D`) against a fixed constant:

```
pattern = 1111111111101001
```

If the data sent matches the `pattern` **exactly**, the output signal `B` is set to `'1'`. This is the control signal seen feeding into the **Logic** block in the schematic above.

[IMAGE: contents of backdoor.vhdl in editor/terminal — remove after replacing]

### 4. tpm.vhdl (top module)

```vhdl
begin
    ck : ckey port map(Key);
    enc: encryption port map (Data, Key, Encrypted);
    bd: backdoor port map (Data, B);

    process(Key, Encrypted, B)
    begin
        case B is
            when '1' =>
                for i in 0 to 15 loop
                    Output(i) <= Key(i);
                end loop;
            when others =>
                for i in 0 to 15 loop
                    Output(i) <= Encrypted(i);
                end loop;
        end case;
    end process;
end Behavioral;
```

This `tpm` module ties all the previous components together. The logic is clear:

- If `B = '1'` (backdoor triggered) → **Output = Key** (the raw internal key is output, bypassing encryption entirely)
- If `B = '0'` (normal condition) → Output = Encrypted (properly encrypted data, as intended)

[IMAGE: contents of tpm.vhdl in editor/terminal — remove after replacing]

## Identifying the Backdoor

Based on the four files above, the overall logic can be summarized as follows:

1. The chip is designed to encrypt every piece of data that passes through it, using the internal `Key`
2. However, there is a special condition (the backdoor): if the input data exactly matches a specific pattern (`1111111111101001`), the encryption mechanism is bypassed, and the chip instead **leaks its internal Key in the clear**

In other words, sending the following data is enough to trigger the backdoor:

```
D = 1111111111101001   (binary)
D = 0xFFE9              (hexadecimal)
```

And the system will respond with the raw Key:

```
Key = 0110001111100001   (binary)
Key = 0x63E1               (hexadecimal)
```

## Connecting to the Satellite

With this understanding, I connected to the satellite using `nc`, based on the information from the **Spawn Docker** page:

```bash
nc 154.57.164.77 31117
```

[IMAGE: nc connection result, including the service's initial prompt/instructions — remove after replacing]

When prompted for input, I sent the backdoor trigger pattern I had identified:

```
1111111111101001
```

[IMAGE: the input sent to the service — remove after replacing]

Following my analysis, the system should respond with the raw internal Key instead of encrypted data.

[IMAGE: the service's response after the backdoor is triggered — remove after replacing]

## Getting the Flag

[IMAGE: the flag received from the service — remove after replacing]

The flag I obtained:

```
HTB{FLAG_GOES_HERE}
```

[IMAGE: proof of successful flag submission (Scenario Pwned) — remove after replacing]

## Conclusion

This challenge demonstrates how a backdoor can be embedded at the hardware description language (VHDL) level, hidden among otherwise legitimate logic such as an encryption routine. By systematically reading the code module by module — starting from the key source, through the encryption process, to the control signal — the backdoor could be identified without any complex simulation, simply by tracing the `if D = pattern` condition that triggers the security bypass in the system.