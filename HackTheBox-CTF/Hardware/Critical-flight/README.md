# [HTB Hardware] Unraveling the Sabotage in the "Critical Flight" PCB — When the Flag Hides Behind a Copper Trace

## Introduction

One thing I enjoy about the *Hardware* category on HackTheBox is that the "source code" isn't a `.py` file or an ELF binary — it's a set of Printed Circuit Board (PCB) production files. Gerber files, to be exact. This challenge is called **Critical Flight**, and its premise felt quite relevant to me, since I also tinker with DIY drones and electronics:

> *"Your team has assigned you to a mission to investigate the production files of Printed Circuit Boards for irregularities. This is in response to the deployment of nonfunctional DIY drones that keep falling out of the sky. The team had used a slightly modified version of an open-source flight controller in order to save time, but it appears that someone had sabotaged the design before production. Can you help identify any suspicious alterations made to the boards?"*

In short: a team used an open-source flight controller design as a base to speed up production, but someone had inserted something into the production files before the PCB was sent to the fab house. My task was to dissect the given Gerber files, look for anomalies, and ultimately locate the flag hidden within them.

![](images/description.png)

## Preparation

### 1. Archive Contents

The provided file is `hw_critical_flight.zip`. After extraction, it contains a single folder named `flight_control_board` holding pure Gerber (RS-274X) files, and there is no KiCad project file (`.kicad_pcb`), no schematic, and no BOM. Here is the complete file listing:

```
flight_control_board/
├── HadesMicro-B_Cu.gbr           
├── HadesMicro-B_Fab.gbr          
├── HadesMicro-B_Mask.gbr         
├── HadesMicro-B_Paste.gbr        
├── HadesMicro-B_Silkscreen.gbr   
├── HadesMicro-Edge_Cuts.gbr      
├── HadesMicro-F_Cu.gbr           
├── HadesMicro-F_Fab.gbr          
├── HadesMicro-F_Mask.gbr         
├── HadesMicro-F_Paste.gbr        
├── HadesMicro-F_Silkscreen.gbr   
├── HadesMicro-In1_Cu.gbr         
└── HadesMicro-In2_Cu.gbr         
```

Just from this file naming scheme, it's already clear that the board named **HadesMicro** is a **4-layer PCB** (Top, In1, In2, Bottom), and fairly common for a small ("micro") flight controller that needs a lot of routing for the MCU, IMU sensor, and motor/ESC connectors within a tight footprint.

![](images/UnzipResult.png)

### 2. Reading Metadata Inside the Gerber Files

A Gerber file isn't a binary file, its content is ASCII text with plotting commands (`G04`, D-codes, X/Y coordinates, etc.). Every file starts with a `G04 #@! TF...` comment block containing standard Gerber X2 *file attributes*, so I could read the production metadata directly without any extra tooling:

```
G04 #@! TF.GenerationSoftware,KiCad,Pcbnew,(6.0.9)*
G04 #@! TF.CreationDate,2023-03-18T16:21:46+02:00*
G04 #@! TF.ProjectId,HadesMicro,48616465-734d-4696-9372-6f2e6b696361,rev?*
G04 #@! TF.SameCoordinates,Original*
G04 #@! TF.FileFunction,Copper,L4,Bot*
G04 #@! TF.FilePolarity,Positive*
```

From this I gathered a few initial facts:

- The board was designed using **KiCad Pcbnew version 6.0.9**.
- The files were generated on **March 18, 2023, 16:21:46 (+02:00)**.
- The project name is **HadesMicro**.
- The `TF.FileFunction` on each layer is consistent with the file naming (`Copper,L4,Bot` for `B_Cu`, `Legend,Top` for `F_Silkscreen`, etc.), meaning no file appeared to have been carelessly renamed/swapped.

### 3. Choosing a Visualization Tool: PCBWay Online Gerber Viewer

Instead of installing a full PCB CAD suite (a full KiCad install, Altium, etc.) purely for visual inspection, I decided to use the free **PCBWay Online Gerber Viewer** service (`pcbway.com/project/OnlineGerberViewer.html`). This tool accepts a Gerber folder/archive directly and renders the entire layer stack (copper, soldermask, silkscreen, solderpaste, inner layers) into a single interactive board view right in the browser — complete with per-layer show/hide toggles and a 3D Viewer option.

I uploaded the `flight_control_board` folder directly into the tool. The panel on the left automatically detected and listed every layer according to the `TF.FileFunction` I had read earlier, grouped into three sections:

- **top**: copper, copper, soldermask, soldermask, silkscreen, silkscreen, solderpaste, solderpaste
- **bottom**: copper, copper, soldermask, soldermask, silkscreen, silkscreen, solderpaste, solderpaste
- **inner**: copper (2 inner layers)

This layout is consistent with the 4-layer structure I had already inferred from the file listing in the previous step.

[IMAGE: initial view of PCBWay OnlineGerberViewer right after uploading the gerber folder — remove after replacing]

---

## Analysis Stage 1 — Reviewing the Top Side via PCBWay Gerber Viewer

With the **top** tab active and all top-side layers (copper, soldermask, silkscreen) displayed together, the PCBWay Gerber Viewer rendered the **HadesMicro** board complete with every component's *reference designator* — something far more informative than a manual render, since the component labels (U1, R1, C1, etc.) are printed exactly where they sit on the actual Fab/Silkscreen layer.

From this render, I was able to map out the board's components far more precisely:

| Reference Designator | Likely Function |
|---|---|
| **MCU1** | Large QFP chip in the bottom-center of the board — the main microcontroller |
| **PWM1** | QFP chip on the mid-left, next to the motor header — likely a PWM driver/expander for motor output |
| **U2** | IC on the mid-right, near USB1 — likely a USB-to-serial chip or an additional sensor |
| **IMU1** | Inertial sensor (gyro/accelerometer), placed near the board's center to minimize vibration |
| **MAG1** | Magnetometer sensor (compass) |
| **HSE1** | Oscillator crystal (*High Speed External clock*) for the MCU |
| **EPROM1** | External EEPROM chip — likely for storing configuration/tuning parameters |
| **BAR1** | Barometer sensor (altitude) |
| **REG1** | Voltage regulator for the power rail |
| **RESET1** | MCU reset button |
| **VIN1** | Main voltage input connector (power in) |
| **TELEM1** | Telemetry connector |
| **RC** | Receiver connector (4-pin) |
| **USB1** | USB port for flashing/configuration |
| **SWD1** | SWD (Serial Wire Debug) header — for flashing firmware directly to the MCU via a debugger |
| **I2C3** | I2C header for external sensors |
| **FLASH1** | External flash memory chip (likely for blackbox logging) |
| **SERVO1** | Auxiliary servo connector |
| **PWR_PWM1** | 3x8 pin header (labeled `I`, `+`, `S`, numbered 1–8) — PWM signal output to motors/ESCs |
| **S / F / MODE** | Three pads labeled S, F, MODE — likely *sensor select*, *flash*, and *boot mode* jumpers |

The **"HADES micro"** logo is silkscreened prominently in the center of the board, and an `X`/`Y` arrow near `EPROM1` marks the board's axis orientation (relevant for IMU calibration when the firmware reads accelerometer/gyro data).

[IMAGE: top layer render of HadesMicro in PCBWay Gerber Viewer with all reference designators visible — remove after replacing]

With such a complete component map, the design looks like a perfectly reasonable and electrically functional AIO (All-In-One) flight controller — MCU, IMU, magnetometer, barometer, power regulator, and even an SWD/USB interface for flashing are all present and logically interconnected. I found no indication of sabotage on this side.

---

## Analysis Stage 2 — Reviewing the Bottom Side

I switched to the **bottom** tab on the PCBWay Gerber Viewer to inspect the layers on the opposite side, enabling the bottom `copper`, `soldermask`, and `silkscreen` layers.

The bottom side revealed additional pinout labels:

- A UART header: `3V3 GND TX RX` and several similar headers — for GPS, telemetry, and OSD/VTX.
- An RC header: `CH1 CH2 CH3 CH4`.
- An I2C header: `SDA SCL GND 3V3`.
- A `PWR`/`GND` header for the main power rail.
- The designer's signature **"philsal.co.uk"** and a small date mark **"12/19"** — reinforcing the narrative that this board is a modified version of a community open-source flight controller (a "Mike Cousins" credit also appears in the PCBWay tool's footer as a Gerber-viewer community contributor, though this is part of the tool's own attribution, not the board design itself).

[IMAGE: bottom layer render of HadesMicro in PCBWay Gerber Viewer — remove after replacing]

### The standout anomaly: hidden text disguised as a copper trace

What caught my attention was a **vertical block of text** on the right side of the board's bottom layer, positioned right next to the `PWR/GND` header and the motor pin grid. At a glance, its shape blends in with the surrounding trace pattern (sharing the same translucent greyish-green color typical of silkscreen), making it easy to miss if you're only glancing at the board in the viewer without zooming in — this is most likely a deliberate disguise by whoever inserted it.

I used the zoom feature in the PCBWay Gerber Viewer to magnify that area, then took a screenshot and corrected the orientation (rotating 180° and flipping horizontally) so the text would read normally — since bottom-side silkscreen is drawn mirrored by default relative to a top-down view of the board.

[IMAGE: zoomed-in view from PCBWay Gerber Viewer of the hidden text area, before orientation correction — remove after replacing]

Once the orientation was corrected, the text read as a leetspeak-style string:

```
HTB{533_7h3_1nn32_w02k1n95
```

[IMAGE: cropped and orientation-corrected hidden text (180° rotation + horizontal flip) — remove after replacing]

The tail end of the string (the closing curly brace `}`) sits right where the silkscreen path curves in toward the large mounting-hole pad in the board corner — in KiCad, silkscreen is automatically clipped (clearance) wherever it overlaps a pad/hole, so the trailing character may have been partially cut off. I couldn't fully confirm the closing character from the viewer alone; maximum zoom or a high-resolution image export would be needed for final confirmation.

[IMAGE: crop of the string's tail end near the mounting hole at maximum zoom in PCBWay Gerber Viewer — remove after replacing]

---

## Root Cause / Vulnerability Conclusion

Based on the analysis above, the "sabotage" in the **HadesMicro** flight controller design **is not a functional electrical fault** (such as a short circuit, a swapped UART RX/TX pin, or a wrong component value) that would directly explain drones "falling out of the sky" from a purely circuit-level standpoint — every reference designator (MCU1, IMU1, MAG1, BAR1, REG1, etc.) shows a coherent, perfectly reasonable flight-controller schematic. What I found instead was:

- A CTF-flag-style string (`HTB{...}`) **inserted as a hidden silkscreen object** on the `HadesMicro-B_Silkscreen.gbr` layer.
- This string was deliberately **placed along a path resembling a copper trace** and given a translucent color that blends with the surrounding board elements, making it invisible to the naked eye unless the board is inspected area by area with zoom.
- This is a form of *visual steganography* embedded in the PCB production file — directly tying into the challenge's narrative: whoever "sabotaged" the design inserted something into the Gerber files before the board was sent to the fab house, and finding evidence of that insertion is exactly what the investigator (the player) is meant to do.

The root cause from a *process* standpoint: the final Gerber files were not visually re-verified layer by layer before being sent to fabrication, allowing the foreign silkscreen insertion to go undetected.

---

## Exploitation (Reproduction Steps)

Here is a summary of the steps I took to reproduce this finding from scratch, using the **PCBWay Online Gerber Viewer**:

1. **Extract the challenge archive**

   ```bash
   unzip hw_critical_flight.zip -d critical_flight
   ```

2. **Open the PCBWay Online Gerber Viewer** at `https://www.pcbway.com/project/OnlineGerberViewer.html`.

3. **Upload the `flight_control_board` folder** (either as a folder or re-zipped) via the upload button in the viewer.

   [IMAGE: process of uploading the gerber folder to PCBWay Gerber Viewer — remove after replacing]

4. **Confirm all top-side layers are loaded** (left panel: `top` group — copper, soldermask, silkscreen, solderpaste) and review every reference designator that appears on the board to map out the components (MCU1, IMU1, PWM1, etc.).

5. **Switch to the `bottom` tab**, enable the bottom `copper`, `soldermask`, and `silkscreen` layers.

6. **Zoom into the upper-right area of the board's bottom side**, around the `PWR/GND` header and the motor pin grid, where a trace-like pattern is actually hidden text.

   [IMAGE: zoomed view of the suspicious area in PCBWay Gerber Viewer — remove after replacing]

7. **Screenshot that area**, then correct the image orientation offline (rotate 180° + horizontal flip) so the text reads correctly, for example using a simple image editor:

   ```python
   from PIL import Image

   im = Image.open("pcbway_zoom_screenshot.png")
   fixed = im.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
   fixed.save("hidden_text_fixed.png")
   ```

[IMAGE: final result after orientation correction, showing the full flag string — remove after replacing]

---

## Flag

From my review in the PCBWay Gerber Viewer, the string I was able to read is:

```
[FLAG: HTB{533_7h3_1nn32_w02k1n95...} — closing character not fully confirmed due to silkscreen clearance near the mounting hole; re-verify with maximum zoom in the PCBWay Gerber Viewer on that area, then replace with the actual flag from a valid HTB submission]
```

[IMAGE: proof of a successful flag submission on the HackTheBox platform — remove after replacing]

---

## Closing Thoughts

The **Critical Flight** challenge was a refreshingly different experience compared to the web or pwn challenges I usually work on — here, the "source code" is a set of PCB manufacturing files, and the debugging process is *visual reverse engineering* of Gerber layers rather than reading lines of code. Using the **PCBWay Online Gerber Viewer** made this process much easier since I didn't need to install any PCB CAD software at all — just upload the Gerber folder and every layer renders instantly in the browser, complete with component reference designators.

The key takeaways for me:

1. Hardware production files (Gerbers, BOM, pick-and-place) should ideally be treated like source code in a software supply chain — they need review/verification before being handed off to a fab house, since they're just as susceptible to unwanted insertions.
2. Silkscreen can be abused as a visual steganography channel, exploiting colors and shapes that resemble other board elements to avoid easy detection.
3. A free browser-based tool like the PCBWay Online Gerber Viewer is more than adequate for visual Gerber inspection without needing paid PCB CAD software, especially since it also renders reference designators from the Fab layer, which is extremely helpful for mapping out components.

I still need to precisely verify the flag's closing character visually before making a final submission. Once confirmed, I'll update the flag section of this write-up accordingly.

Thanks for reading — if you have any input on a more efficient way to read Gerber files, I'd be glad to discuss it.