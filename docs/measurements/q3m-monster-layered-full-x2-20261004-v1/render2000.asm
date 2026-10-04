Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  000000014032EE90: push        rbp
  000000014032EE92: push        rsi
  000000014032EE93: push        rdi
  000000014032EE94: push        r12
  000000014032EE96: push        r13
  000000014032EE98: push        r14
  000000014032EE9A: push        r15
  000000014032EE9C: lea         rbp,[rsp-7]
  000000014032EEA1: sub         rsp,0A0h
  000000014032EEA8: mov         rax,qword ptr [00000001406649D8h]
  000000014032EEAF: xor         rax,rsp
  000000014032EEB2: mov         qword ptr [rbp-9],rax
  000000014032EEB6: mov         rax,qword ptr [rbp+67h]
  000000014032EEBA: mov         rsi,rcx
  000000014032EEBD: mov         rcx,qword ptr [rbp+0000000000000087h]
  000000014032EEC4: mov         r12,rdx
  000000014032EEC7: movups      xmm0,xmmword ptr [r9]
  000000014032EECB: mov         edi,dword ptr [rbp+000000000000009Fh]
  000000014032EED1: mov         r14,qword ptr [rbp+6Fh]
  000000014032EED5: movzx       r13d,byte ptr [rbp+00000000000000A7h]
  000000014032EEDD: mov         qword ptr [rbp-51h],rcx
  000000014032EEE1: mov         rcx,qword ptr [rbp+00000000000000AFh]
  000000014032EEE8: mov         qword ptr [rbp-49h],rcx
  000000014032EEEC: mov         rcx,qword ptr [rax]
  000000014032EEEF: mov         qword ptr [rbp-59h],rcx
  000000014032EEF3: shr         rcx,20h
  000000014032EEF7: add         ecx,edi
  000000014032EEF9: movaps      xmmword ptr [rbp-29h],xmm0
  000000014032EEFD: cmp         dword ptr [000000014070FD18h],0
  000000014032EF04: mov         dword ptr [rbp-55h],ecx
  000000014032EF07: mov         ecx,dword ptr [rbp+77h]
  000000014032EF0A: je          000000014032EF34
  000000014032EF0C: movzx       eax,byte ptr [rsi+0000000000001739h]
  000000014032EF13: cmp         word ptr [rsi+000000000000172Ah],ax
  000000014032EF1A: jle         000000014032EF22
  000000014032EF1C: or          ecx,dword ptr [00000001405A234Ch]
  000000014032EF22: test        r13b,r13b
  000000014032EF25: jne         000000014032EF37
  000000014032EF27: mov         eax,dword ptr [00000001405A2348h]
  000000014032EF2D: or          eax,1
  000000014032EF30: or          ecx,eax
  000000014032EF32: jmp         000000014032EF3D
  000000014032EF34: or          ecx,4
  000000014032EF37: or          ecx,dword ptr [00000001405A2344h]
  000000014032EF3D: mov         r15d,ecx
  000000014032EF40: mov         qword ptr [rsp+20h],r14
  000000014032EF45: or          r15d,2
  000000014032EF49: lea         r9,[rbp-59h]
  000000014032EF4D: test        r13b,r13b
  000000014032EF50: lea         rdx,[rbp-29h]
  000000014032EF54: cmove       r15d,ecx
  000000014032EF58: mov         rcx,r12
  000000014032EF5B: mov         r8d,r15d
  000000014032EF5E: call        000000014029E1B0
  000000014032EF63: mov         r8d,r15d
  000000014032EF66: lea         rdx,[rbp-29h]
  000000014032EF6A: mov         rcx,r12
  000000014032EF6D: call        000000014029E190
  000000014032EF72: test        eax,eax
  000000014032EF74: je          000000014032F350
  000000014032EF7A: cmp         dword ptr [rsi+0000000000000BA8h],0
  000000014032EF81: mov         qword ptr [rsp+00000000000000F0h],rbx
  000000014032EF89: je          000000014032EFD0
  000000014032EF8B: mov         rcx,qword ptr [rsi+0000000000000CB0h]
  000000014032EF92: call        00000001403F6D50
  000000014032EF97: mov         rbx,qword ptr [rsi+0000000000000CB0h]
  000000014032EF9E: mov         rcx,rbx
  000000014032EFA1: call        00000001403F7890
  000000014032EFA6: mov         rcx,rbx
  000000014032EFA9: mov         edi,eax
  000000014032EFAB: call        00000001403F78B0
  000000014032EFB0: movzx       r9d,word ptr [00000001405C0678h]
  000000014032EFB8: mov         rdx,rax
  000000014032EFBB: mov         rcx,qword ptr [rsi+0000000000000CD8h]
  000000014032EFC2: mov         r8d,edi
  000000014032EFC5: call        00000001404123C0
  000000014032EFCA: mov         edi,dword ptr [rbp+000000000000009Fh]
  000000014032EFD0: mov         rcx,qword ptr [rsi+0000000000000CD8h]
  000000014032EFD7: mov         ebx,dword ptr [rbp+7Fh]
  000000014032EFDA: add         rcx,8
  000000014032EFDE: mov         edx,ebx
  000000014032EFE0: call        0000000140412690
  000000014032EFE5: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032EFEC: je          000000014032F005
  000000014032EFEE: mov         rcx,qword ptr [rsi+0000000000001200h]
  000000014032EFF5: test        rcx,rcx
  000000014032EFF8: je          000000014032F005
  000000014032EFFA: add         rcx,8
  000000014032EFFE: mov         edx,ebx
  000000014032F000: call        0000000140412690
  000000014032F005: cmp         dword ptr [000000014070FD18h],0
  000000014032F00C: je          000000014032F037
  000000014032F00E: movsx       ecx,word ptr [rsi+000000000000172Ah]
  000000014032F015: movzx       eax,byte ptr [rsi+0000000000001739h]
  000000014032F01C: cmp         ecx,eax
  000000014032F01E: jle         000000014032F037
  000000014032F020: mov         eax,10h
  000000014032F025: sub         eax,ecx
  000000014032F027: and         eax,8000000Fh
  000000014032F02C: jge         000000014032F03E
  000000014032F02E: dec         eax
  000000014032F030: or          eax,0FFFFFFF0h
  000000014032F033: inc         eax
  000000014032F035: jmp         000000014032F03E
  000000014032F037: movzx       eax,word ptr [rsi+000000000000172Ah]
  000000014032F03E: movsx       rcx,ax
  000000014032F042: cmp         ecx,0Fh
  000000014032F045: ja          000000014032F1E4
  000000014032F04B: lea         rdx,[0000000140000000h]
  000000014032F052: mov         ecx,dword ptr [rdx+rcx*4+000000000032F370h]
  000000014032F059: add         rcx,rdx
  000000014032F05C: jmp         rcx
  000000014032F05E: mov         r9d,dword ptr [r14+4]
  000000014032F062: mov         rcx,r12
  000000014032F065: mov         r8d,dword ptr [r14]
  000000014032F068: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F06F: movzx       ebx,r13b
  000000014032F073: mov         dword ptr [rsp+28h],ebx
  000000014032F077: mov         dword ptr [rsp+20h],r15d
  000000014032F07C: call        000000014029E260
  000000014032F081: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F088: je          000000014032F1E4
  000000014032F08E: jmp         000000014032F1C0
  000000014032F093: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F09A: je          000000014032F0CD
  000000014032F09C: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F0A3: jne         000000014032F0CD
  000000014032F0A5: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F0AC: test        rdx,rdx
  000000014032F0AF: je          000000014032F0CD
  000000014032F0B1: mov         r9d,dword ptr [r14+4]
  000000014032F0B5: mov         rcx,r12
  000000014032F0B8: mov         r8d,dword ptr [r14]
  000000014032F0BB: movzx       eax,r13b
  000000014032F0BF: mov         dword ptr [rsp+28h],eax
  000000014032F0C3: mov         dword ptr [rsp+20h],r15d
  000000014032F0C8: call        000000014029E260
  000000014032F0CD: mov         r9d,dword ptr [r14+4]
  000000014032F0D1: mov         rcx,r12
  000000014032F0D4: mov         r8d,dword ptr [r14]
  000000014032F0D7: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F0DE: movzx       ebx,r13b
  000000014032F0E2: mov         dword ptr [rsp+28h],ebx
  000000014032F0E6: mov         dword ptr [rsp+20h],r15d
  000000014032F0EB: call        000000014029E260
  000000014032F0F0: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F0F7: je          000000014032F1E4
  000000014032F0FD: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F104: je          000000014032F1E4
  000000014032F10A: jmp         000000014032F1C0
  000000014032F10F: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F116: je          000000014032F140
  000000014032F118: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F11F: test        rdx,rdx
  000000014032F122: je          000000014032F140
  000000014032F124: mov         r9d,dword ptr [r14+4]
  000000014032F128: mov         rcx,r12
  000000014032F12B: mov         r8d,dword ptr [r14]
  000000014032F12E: movzx       eax,r13b
  000000014032F132: mov         dword ptr [rsp+28h],eax
  000000014032F136: mov         dword ptr [rsp+20h],r15d
  000000014032F13B: call        000000014029E260
  000000014032F140: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F147: movzx       eax,r13b
  000000014032F14B: mov         dword ptr [rsp+28h],eax
  000000014032F14F: jmp         000000014032F1D0
  000000014032F151: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F158: je          000000014032F18B
  000000014032F15A: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F161: je          000000014032F18B
  000000014032F163: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F16A: test        rdx,rdx
  000000014032F16D: je          000000014032F18B
  000000014032F16F: mov         r9d,dword ptr [r14+4]
  000000014032F173: mov         rcx,r12
  000000014032F176: mov         r8d,dword ptr [r14]
  000000014032F179: movzx       eax,r13b
  000000014032F17D: mov         dword ptr [rsp+28h],eax
  000000014032F181: mov         dword ptr [rsp+20h],r15d
  000000014032F186: call        000000014029E260
  000000014032F18B: mov         r9d,dword ptr [r14+4]
  000000014032F18F: mov         rcx,r12
  000000014032F192: mov         r8d,dword ptr [r14]
  000000014032F195: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F19C: movzx       ebx,r13b
  000000014032F1A0: mov         dword ptr [rsp+28h],ebx
  000000014032F1A4: mov         dword ptr [rsp+20h],r15d
  000000014032F1A9: call        000000014029E260
  000000014032F1AE: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F1B5: je          000000014032F1E4
  000000014032F1B7: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F1BE: jne         000000014032F1E4
  000000014032F1C0: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F1C7: test        rdx,rdx
  000000014032F1CA: je          000000014032F1E4
  000000014032F1CC: mov         dword ptr [rsp+28h],ebx
  000000014032F1D0: mov         r9d,dword ptr [r14+4]
  000000014032F1D4: mov         rcx,r12
  000000014032F1D7: mov         r8d,dword ptr [r14]
  000000014032F1DA: mov         dword ptr [rsp+20h],r15d
  000000014032F1DF: call        000000014029E260
  000000014032F1E4: mov         rcx,qword ptr [rbp-51h]
  000000014032F1E8: mov         r9d,edi
  000000014032F1EB: mov         r8d,dword ptr [rbp-55h]
  000000014032F1EF: mov         edx,dword ptr [rbp-59h]
  000000014032F1F2: sub         r8d,edi
  000000014032F1F5: mov         dword ptr [rsp+38h],r15d
  000000014032F1FA: mov         eax,dword ptr [rcx]
  000000014032F1FC: mov         dword ptr [rbp-19h],eax
  000000014032F1FF: mov         eax,dword ptr [rcx+4]
  000000014032F202: sub         eax,edi
  000000014032F204: mov         dword ptr [rbp-15h],eax
  000000014032F207: mov         eax,dword ptr [rcx+8]
  000000014032F20A: mov         dword ptr [rbp-11h],eax
  000000014032F20D: mov         eax,dword ptr [rcx+0Ch]
  000000014032F210: mov         rcx,r12
  000000014032F213: sub         eax,edi
  000000014032F215: mov         dword ptr [rbp-0Dh],eax
  000000014032F218: movzx       eax,byte ptr [rbp+000000000000008Fh]
  000000014032F21F: mov         byte ptr [rsp+30h],al
  000000014032F223: lea         rax,[rbp-19h]
  000000014032F227: mov         qword ptr [rsp+28h],rax
  000000014032F22C: mov         qword ptr [rsp+20h],r14
  000000014032F231: call        000000014029E4C0
  000000014032F236: cmp         dword ptr [rbp+0000000000000097h],0
  000000014032F23D: lea         r9,[rbp-51h]
  000000014032F241: mov         rbx,qword ptr [rsp+00000000000000F0h]
  000000014032F249: mov         edx,r15d
  000000014032F24C: je          000000014032F26C
  000000014032F24E: mov         ecx,dword ptr [r14]
  000000014032F251: lea         r8,[rbp-29h]
  000000014032F255: add         ecx,dword ptr [rbp-59h]
  000000014032F258: mov         rax,qword ptr [rbp-59h]
  000000014032F25C: shr         rax,20h
  000000014032F260: add         eax,dword ptr [r14+4]
  000000014032F264: mov         dword ptr [rbp-4Dh],eax
  000000014032F267: mov         dword ptr [rbp-51h],ecx
  000000014032F26A: jmp         000000014032F275
  000000014032F26C: xor         eax,eax
  000000014032F26E: mov         qword ptr [rbp-51h],rax
  000000014032F272: xor         r8d,r8d
  000000014032F275: mov         rcx,r12
  000000014032F278: call        000000014029EA40
  000000014032F27D: movaps      xmm0,xmmword ptr [rbp-29h]
  000000014032F281: lea         rcx,[rbp-39h]
  000000014032F285: xor         r8d,r8d
  000000014032F288: movdqa      xmmword ptr [rbp-39h],xmm0
  000000014032F28D: xor         edx,edx
  000000014032F28F: cmp         byte ptr [rsi+20h],dl
  000000014032F292: je          000000014032F2B7
  000000014032F294: lea         r9d,[r8+5]
  000000014032F298: mov         dword ptr [rsp+20h],5
  000000014032F2A0: call        0000000140407B20
  000000014032F2A5: add         dword ptr [rbp-39h],2
  000000014032F2A9: add         dword ptr [rbp-31h],2
  000000014032F2AD: add         dword ptr [rbp-35h],2
  000000014032F2B1: add         dword ptr [rbp-2Dh],2
  000000014032F2B5: jmp         000000014032F2D6
  000000014032F2B7: mov         r9d,2
  000000014032F2BD: mov         dword ptr [rsp+20h],2
  000000014032F2C5: call        0000000140407B20
  000000014032F2CA: inc         dword ptr [rbp-39h]
  000000014032F2CD: inc         dword ptr [rbp-31h]
  000000014032F2D0: inc         dword ptr [rbp-35h]
  000000014032F2D3: inc         dword ptr [rbp-2Dh]
  000000014032F2D6: cmp         byte ptr [rsi+20h],0
  000000014032F2DA: je          000000014032F308
  000000014032F2DC: mov         ecx,r15d
  000000014032F2DF: and         ecx,10000000h
  000000014032F2E5: or          ecx,28000000h
  000000014032F2EB: shr         ecx,1Bh
  000000014032F2EE: call        0000000140413220
  000000014032F2F3: mov         rdx,qword ptr [rbp-49h]
  000000014032F2F7: mov         rcx,rsi
  000000014032F2FA: call        0000000140329120
  000000014032F2FF: mov         ecx,eax
  000000014032F301: call        0000000140413200
  000000014032F306: jmp         000000014032F30F
  000000014032F308: xor         ecx,ecx
  000000014032F30A: call        0000000140413220
  000000014032F30F: movaps      xmm0,xmmword ptr [rbp-39h]
  000000014032F313: lea         rax,[rbp-49h]
  000000014032F317: mov         r9d,dword ptr [rbp-55h]
  000000014032F31B: lea         rdx,[rbp-29h]
  000000014032F31F: mov         r8d,dword ptr [rbp-59h]
  000000014032F323: mov         rcx,r12
  000000014032F326: mov         qword ptr [rsp+38h],rax
  000000014032F32B: mov         eax,dword ptr [r14+4]
  000000014032F32F: mov         dword ptr [rsp+30h],r15d
  000000014032F334: mov         dword ptr [rsp+28h],eax
  000000014032F338: mov         eax,dword ptr [r14]
  000000014032F33B: mov         dword ptr [rsp+20h],eax
  000000014032F33F: movdqa      xmmword ptr [rbp-49h],xmm0
  000000014032F344: call        000000014029DFF0
  000000014032F349: xor         ecx,ecx
  000000014032F34B: call        0000000140413220
  000000014032F350: mov         rcx,qword ptr [rbp-9]
  000000014032F354: xor         rcx,rsp
  000000014032F357: call        00000001404F77A0
  000000014032F35C: add         rsp,0A0h
  000000014032F363: pop         r15
  000000014032F365: pop         r14
  000000014032F367: pop         r13
  000000014032F369: pop         r12
  000000014032F36B: pop         rdi
  000000014032F36C: pop         rsi
  000000014032F36D: pop         rbp
  000000014032F36E: ret
  000000014032F36F: nop
  000000014032F370: pop         rsi
  000000014032F371: lock xor    al,byte ptr [rax]
  000000014032F374: pop         rsi
  000000014032F375: lock xor    al,byte ptr [rax]
  000000014032F378: pop         rsi
  000000014032F379: lock xor    al,byte ptr [rax]
  000000014032F37C: xchg        eax,ebx
  000000014032F37D: lock xor    al,byte ptr [rax]
  000000014032F380: xchg        eax,ebx
  000000014032F381: lock xor    al,byte ptr [rax]
  000000014032F384: xchg        eax,ebx
  000000014032F385: lock xor    al,byte ptr [rax]
  000000014032F388: xchg        eax,ebx
  000000014032F389: lock xor    al,byte ptr [rax]
  000000014032F38C: xchg        eax,ebx
  000000014032F38D: lock xor    al,byte ptr [rax]
  000000014032F390: psllw       mm6,mmword ptr [rdx]
  000000014032F393: add         byte ptr [rcx-0Fh],dl
  000000014032F396: xor         al,byte ptr [rax]
  000000014032F398: push        rcx
  000000014032F399: F1
  000000014032F39A: xor         al,byte ptr [rax]
  000000014032F39C: push        rcx
  000000014032F39D: F1
  000000014032F39E: xor         al,byte ptr [rax]
  000000014032F3A0: push        rcx
  000000014032F3A1: F1
  000000014032F3A2: xor         al,byte ptr [rax]
  000000014032F3A4: push        rcx
  000000014032F3A5: F1
  000000014032F3A6: xor         al,byte ptr [rax]
  000000014032F3A8: push        rcx
  000000014032F3A9: F1
  000000014032F3AA: xor         al,byte ptr [rax]
  000000014032F3AC: push        rcx
  000000014032F3AD: F1
  000000014032F3AE: xor         al,byte ptr [rax]
  000000014032F3B0: 40

  Summary

      589000 .text
