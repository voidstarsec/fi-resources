import os
import sys

GLITCH_RESULTS = {
    0 : 'BOOT_MODE',
    1 : 'SWD_ENABLE',
    2 : 'FLASH_READ',
}

class GlitchResult:

    def __init__(self,x,y,z,offset,result):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.offset = int(offset)
        self.result = result

    def __str__(self):
        return f"X: {self.x} Y: {self.y} Z: {self.z} Offset: {self.offset} Result: {GLITCH_RESULTS[self.result]}"

def parse_results(result_path):
    glitches = []
    with open(result_path,'r') as infile:
        results = infile.readlines()
        for line in results:
            if 'Boot' in line:
                result = 1 if "SWD" in line else 0
                vals = line.split(':')
                glitches.append(GlitchResult(vals[1].split('-')[0], 
                                             vals[2].split(" ")[1], 
                                             0, 
                                             vals[3].strip(),
                                             result))
    return glitches

'''
Answer the following
- How many boot mode glitches vs SWD glitches?
- For each, which regions were more reliable?
- For each, which offsets were more reliable?

'''
def GenerateStats(glitches):
    boot_glitches = []
    swd_glitches = []
    for glitch in glitches:
        swd_glitches.append(glitch) if glitch.result == 1 else boot_glitches.append(glitch)
    print(f"Boot Mode Glitches Total: {len(boot_glitches)}")
    print(f"SWD Glitches Total: {len(swd_glitches)}")
    ext_offsets = {}
    for glitch in boot_glitches:
        if glitch.offset not in ext_offsets:
            ext_offsets[glitch.offset] = 1
        else:
            ext_offsets[glitch.offset]+=1
    test = sorted(ext_offsets, key=ext_offsets.get, reverse=True)
    print(f"Top 5 EXT Offsets for Boot Mode Bypass: {test[0:5]}")
    ext_offsets = {}
    for glitch in swd_glitches:
        if glitch.offset not in ext_offsets:
            ext_offsets[glitch.offset] = 1
        else:
            ext_offsets[glitch.offset]+=1
    test = sorted(ext_offsets, key=ext_offsets.get, reverse=True)
    print(f"Top 5 EXT Offsets for SWD Enable: {test[0:5]}")



if __name__ == "__main__":
    glitches = parse_results(sys.argv[1])
    GenerateStats(glitches)
