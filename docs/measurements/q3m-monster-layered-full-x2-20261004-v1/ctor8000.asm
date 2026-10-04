Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  00000001403119A0: mov         qword ptr [rsp+20h],rbx
  00000001403119A5: push        rbp
  00000001403119A6: push        rsi
  00000001403119A7: push        rdi
  00000001403119A8: push        r12
  00000001403119AA: push        r13
  00000001403119AC: push        r14
  00000001403119AE: push        r15
  00000001403119B0: sub         rsp,40h
  00000001403119B4: mov         rax,qword ptr [00000001406649D8h]
  00000001403119BB: xor         rax,rsp
  00000001403119BE: mov         qword ptr [rsp+38h],rax
  00000001403119C3: movzx       r14d,dx
  00000001403119C7: mov         rsi,r8
  00000001403119CA: mov         word ptr [rsp+28h],r14w
  00000001403119D0: mov         rbx,rcx
  00000001403119D3: mov         word ptr [rsp+20h],r9w
  00000001403119D9: call        00000001403074D0
  00000001403119DE: lea         rax,[00000001405AA840h]
  00000001403119E5: mov         qword ptr [rbx],rax
  00000001403119E8: lea         r13,[rbx+0000000000000CF0h]
  00000001403119EF: mov         rax,qword ptr [000000014065CB10h]
  00000001403119F6: lea         rdi,[rbx+0000000000000CD0h]
  00000001403119FD: mov         rcx,r13
  0000000140311A00: mov         qword ptr [rdi],rax
  0000000140311A03: call        0000000140410F70
  0000000140311A08: lea         rcx,[rbx+0000000000000E28h]
  0000000140311A0F: call        0000000140410F70
  0000000140311A14: lea         rcx,[rbx+0000000000000F60h]
  0000000140311A1B: call        0000000140410F70
  0000000140311A20: lea         rcx,[rbx+0000000000001098h]
  0000000140311A27: call        0000000140410F70
  0000000140311A2C: movzx       edx,word ptr [00000001405C067Ch]
  0000000140311A33: lea         rbp,[rbx+00000000000011D0h]
  0000000140311A3A: mov         rcx,rbp
  0000000140311A3D: call        0000000140421010
  0000000140311A42: lea         rcx,[rbx+0000000000001218h]
  0000000140311A49: call        0000000140410F70
  0000000140311A4E: lea         rcx,[rbx+0000000000001350h]
  0000000140311A55: call        0000000140410F70
  0000000140311A5A: lea         rcx,[rbx+0000000000001488h]
  0000000140311A61: call        0000000140410F70
  0000000140311A66: lea         rcx,[rbx+00000000000015C0h]
  0000000140311A6D: call        0000000140410F70
  0000000140311A72: movzx       edx,word ptr [00000001405C067Ch]
  0000000140311A79: lea         rcx,[rbx+00000000000016F8h]
  0000000140311A80: call        0000000140421010
  0000000140311A85: mov         rax,qword ptr [000000014065CB10h]
  0000000140311A8C: lea         r15,[rbx+0000000000001740h]
  0000000140311A93: mov         qword ptr [r15],rax
  0000000140311A96: lea         rcx,[00000001405AB1F8h]
  0000000140311A9D: mov         rax,qword ptr [000000014065CB10h]
  0000000140311AA4: xor         edx,edx
  0000000140311AA6: mov         qword ptr [r15+8],rax
  0000000140311AAA: mov         dword ptr [rbx+0000000000001734h],edx
  0000000140311AB0: mov         byte ptr [rbx+0000000000001750h],dl
  0000000140311AB6: mov         dword ptr [rbx+0000000000001754h],edx
  0000000140311ABC: mov         edx,r14d
  0000000140311ABF: mov         word ptr [rbx+8],r14w
  0000000140311AC4: mov         dword ptr [rbx+0000000000001738h],1
  0000000140311ACE: mov         qword ptr [rbx+000000000000172Ch],1
  0000000140311AD9: mov         dword ptr [rbx+24h],0FFFFFFFFh
  0000000140311AE0: mov         dword ptr [rbx+30h],0A0000h
  0000000140311AE7: mov         dword ptr [rbx+34h],0AFFF6h
  0000000140311AEE: mov         dword ptr [rbx+38h],0FFF6h
  0000000140311AF5: mov         dword ptr [rbx+3Ch],0FFF6FFF6h
  0000000140311AFC: mov         dword ptr [rbx+40h],0FFF60000h
  0000000140311B03: mov         dword ptr [rbx+44h],0FFF6000Ah
  0000000140311B0A: mov         dword ptr [rbx+48h],0Ah
  0000000140311B11: mov         dword ptr [rbx+4Ch],0A000Ah
  0000000140311B18: call        0000000140400170
  0000000140311B1D: mov         rdx,rax
  0000000140311B20: lea         rcx,[rsp+30h]
  0000000140311B25: call        00000001403FF7C0
  0000000140311B2A: mov         rcx,rbx
  0000000140311B2D: mov         rdx,qword ptr [rax]
  0000000140311B30: call        0000000140340610
  0000000140311B35: test        al,al
  0000000140311B37: jne         0000000140311C77
  0000000140311B3D: and         r14d,0F00h
  0000000140311B44: je          0000000140311C39
  0000000140311B4A: cmp         r14d,100h
  0000000140311B51: je          0000000140311BF4
  0000000140311B57: cmp         r14d,200h
  0000000140311B5E: je          0000000140311B95
  0000000140311B60: cmp         r14d,300h
  0000000140311B67: jne         0000000140311C77
  0000000140311B6D: lea         rdx,[00000001405AC0C4h]
  0000000140311B74: mov         word ptr [rbx+0Ah],707h
  0000000140311B7A: mov         rcx,rdi
  0000000140311B7D: call        00000001403FD810
  0000000140311B82: lea         rdx,[00000001405EB7ADh]
  0000000140311B89: mov         dword ptr [rbx+0000000000001738h],0
  0000000140311B93: jmp         0000000140311BB1
  0000000140311B95: lea         rdx,[00000001405AC0BCh]
  0000000140311B9C: mov         word ptr [rbx+0Ah],606h
  0000000140311BA2: mov         rcx,rdi
  0000000140311BA5: call        00000001403FD810
  0000000140311BAA: lea         rdx,[00000001405AC078h]
  0000000140311BB1: mov         rcx,r15
  0000000140311BB4: mov         dword ptr [rbx+24h],7
  0000000140311BBB: mov         dword ptr [rbx+0000000000001754h],1
  0000000140311BC5: call        00000001403FD810
  0000000140311BCA: lea         rcx,[rbx+0000000000001748h]
  0000000140311BD1: lea         rdx,[00000001405EB7ADh]
  0000000140311BD8: call        00000001403FD810
  0000000140311BDD: lea         rax,[00000001405AB538h]
  0000000140311BE4: mov         byte ptr [rbx+00000000000005F0h],3
  0000000140311BEB: mov         qword ptr [rbx+28h],rax
  0000000140311BEF: jmp         0000000140311C77
  0000000140311BF4: lea         rdx,[00000001405AC0B0h]
  0000000140311BFB: mov         byte ptr [rbx+0000000000001750h],1
  0000000140311C02: mov         rcx,rdi
  0000000140311C05: mov         word ptr [rbx+0Ah],606h
  0000000140311C0B: call        00000001403FD810
  0000000140311C10: lea         rdx,[00000001405AC0B8h]
  0000000140311C17: mov         dword ptr [rbx+0000000000001738h],0
  0000000140311C21: mov         rcx,r15
  0000000140311C24: mov         dword ptr [rbx+24h],5
  0000000140311C2B: call        00000001403FD810
  0000000140311C30: lea         rdx,[00000001405EB7ADh]
  0000000140311C37: jmp         0000000140311C6B
  0000000140311C39: lea         rdx,[00000001405AC0A8h]
  0000000140311C40: mov         word ptr [rbx+0Ah],606h
  0000000140311C46: mov         rcx,rdi
  0000000140311C49: mov         dword ptr [rbx+24h],5
  0000000140311C50: call        00000001403FD810
  0000000140311C55: lea         rdx,[00000001405EB7ADh]
  0000000140311C5C: mov         rcx,r15
  0000000140311C5F: call        00000001403FD810
  0000000140311C64: lea         rdx,[00000001405AC088h]
  0000000140311C6B: lea         rcx,[rbx+0000000000001748h]
  0000000140311C72: call        00000001403FD810
  0000000140311C77: mov         rax,qword ptr [0000000140667548h]
  0000000140311C7E: movzx       r8d,byte ptr [rbx+0Ah]
  0000000140311C83: movzx       edx,word ptr [rsp+28h]
  0000000140311C88: mov         rcx,qword ptr [rax+0000000000001090h]
  0000000140311C8F: call        000000014023AE30
  0000000140311C94: lea         rdx,[00000001405EB7ADh]
  0000000140311C9B: mov         byte ptr [rbx+0Bh],al
  0000000140311C9E: lea         rcx,[rbx+00000000000005F7h]
  0000000140311CA5: mov         byte ptr [rbx+0Ah],al
  0000000140311CA8: call        00000001403FFA80
  0000000140311CAD: test        eax,eax
  0000000140311CAF: je          0000000140311CC5
  0000000140311CB1: mov         r8,rdi
  0000000140311CB4: lea         rdx,[rsp+30h]
  0000000140311CB9: lea         rcx,[rbx+00000000000005F7h]
  0000000140311CC0: call        00000001403FF890
  0000000140311CC5: mov         rcx,rbx
  0000000140311CC8: call        0000000140316900
  0000000140311CCD: lea         r8,[00000001405AB498h]
  0000000140311CD4: mov         rdx,rdi
  0000000140311CD7: lea         rcx,[rsp+30h]
  0000000140311CDC: call        00000001403FD8E0
  0000000140311CE1: mov         rdx,rax
  0000000140311CE4: lea         rcx,[rsp+28h]
  0000000140311CE9: call        00000001403FF710
  0000000140311CEE: mov         r9d,1
  0000000140311CF4: lea         rcx,[rbx+0000000000000DF8h]
  0000000140311CFB: mov         r8d,r9d
  0000000140311CFE: lea         rdx,[rsp+28h]
  0000000140311D03: call        000000014014D080
  0000000140311D08: lea         rcx,[rsp+30h]
  0000000140311D0D: call        00000001403FD740
  0000000140311D12: lea         r8,[00000001405ABA80h]
  0000000140311D19: mov         rdx,rdi
  0000000140311D1C: lea         rcx,[rsp+28h]
  0000000140311D21: call        00000001403FD8E0
  0000000140311D26: mov         rdx,rax
  0000000140311D29: lea         rcx,[rsp+30h]
  0000000140311D2E: call        00000001403FF710
  0000000140311D33: mov         r9d,1
  0000000140311D39: lea         rcx,[rbx+0000000000001068h]
  0000000140311D40: mov         r8d,r9d
  0000000140311D43: lea         rdx,[rsp+30h]
  0000000140311D48: call        000000014014D080
  0000000140311D4D: lea         rcx,[rsp+28h]
  0000000140311D52: call        00000001403FD740
  0000000140311D57: cmp         dword ptr [000000014070FD18h],0
  0000000140311D5E: jne         0000000140311DEE
  0000000140311D64: lea         r8,[00000001405AB5A8h]
  0000000140311D6B: mov         rdx,rdi
  0000000140311D6E: lea         rcx,[rsp+28h]
  0000000140311D73: call        00000001403FD8E0
  0000000140311D78: mov         rdx,rax
  0000000140311D7B: lea         rcx,[rsp+30h]
  0000000140311D80: call        00000001403FF710
  0000000140311D85: mov         r9d,1
  0000000140311D8B: lea         rcx,[rbx+0000000000000F30h]
  0000000140311D92: mov         r8d,r9d
  0000000140311D95: lea         rdx,[rsp+30h]
  0000000140311D9A: call        000000014014D080
  0000000140311D9F: lea         rcx,[rsp+28h]
  0000000140311DA4: call        00000001403FD740
  0000000140311DA9: lea         r8,[00000001405ABAECh]
  0000000140311DB0: mov         rdx,rdi
  0000000140311DB3: lea         rcx,[rsp+28h]
  0000000140311DB8: call        00000001403FD8E0
  0000000140311DBD: mov         rdx,rax
  0000000140311DC0: lea         rcx,[rsp+30h]
  0000000140311DC5: call        00000001403FF710
  0000000140311DCA: mov         r9d,1
  0000000140311DD0: lea         rcx,[rbx+00000000000011A0h]
  0000000140311DD7: mov         r8d,r9d
  0000000140311DDA: lea         rdx,[rsp+30h]
  0000000140311DDF: call        000000014014D080
  0000000140311DE4: lea         rcx,[rsp+28h]
  0000000140311DE9: call        00000001403FD740
  0000000140311DEE: cmp         dword ptr [rbx+0000000000001738h],0
  0000000140311DF5: mov         qword ptr [rbx+0000000000000CE0h],r13
  0000000140311DFC: je          0000000140311E88
  0000000140311E02: xor         dil,dil
  0000000140311E05: nop         word ptr [rax+rax+0000000000000000h]
  0000000140311E10: mov         rax,qword ptr [0000000140667548h]
  0000000140311E17: mov         rcx,rbp
  0000000140311E1A: movzx       r8d,byte ptr [rsi]
  0000000140311E1E: movzx       edx,dil
  0000000140311E22: mov         r9,qword ptr [rax+0000000000001090h]
  0000000140311E29: add         r9,63D8h
  0000000140311E30: call        00000001404221C0
  0000000140311E35: inc         dil
  0000000140311E38: lea         rsi,[rsi+1]
  0000000140311E3C: cmp         dil,7
  0000000140311E40: jb          0000000140311E10
  0000000140311E42: mov         rdx,rbp
  0000000140311E45: mov         rcx,r13
  0000000140311E48: call        0000000140412390
  0000000140311E4D: mov         rdx,rbp
  0000000140311E50: lea         rcx,[rbx+0000000000000F60h]
  0000000140311E57: call        0000000140412390
  0000000140311E5C: cmp         dword ptr [000000014070FD18h],0
  0000000140311E63: lea         rdi,[rbx+0000000000000E28h]
  0000000140311E6A: jne         0000000140311E8F
  0000000140311E6C: mov         rdx,rbp
  0000000140311E6F: mov         rcx,rdi
  0000000140311E72: call        0000000140412390
  0000000140311E77: mov         rdx,rbp
  0000000140311E7A: lea         rcx,[rbx+0000000000001098h]
  0000000140311E81: call        0000000140412390
  0000000140311E86: jmp         0000000140311E8F
  0000000140311E88: lea         rdi,[rbx+0000000000000E28h]
  0000000140311E8F: mov         rax,qword ptr [rbx+0000000000000CE0h]
  0000000140311E96: mov         qword ptr [rbx+0000000000000CE8h],rdi
  0000000140311E9D: xor         edi,edi
  0000000140311E9F: mov         qword ptr [rbx+0000000000000CD8h],rax
  0000000140311EA6: mov         qword ptr [rbx+0000000000001208h],rdi
  0000000140311EAD: cmp         dword ptr [rbx+0000000000001738h],edi
  0000000140311EB3: je          0000000140311F09
  0000000140311EB5: lea         rdx,[rbx+00000000000016F8h]
  0000000140311EBC: lea         rcx,[rbx+0000000000001218h]
  0000000140311EC3: call        0000000140412390
  0000000140311EC8: lea         rdx,[rbx+00000000000016F8h]
  0000000140311ECF: lea         rcx,[rbx+0000000000001488h]
  0000000140311ED6: call        0000000140412390
  0000000140311EDB: cmp         dword ptr [000000014070FD18h],edi
  0000000140311EE1: jne         0000000140311F09
  0000000140311EE3: lea         rdx,[rbx+00000000000016F8h]
  0000000140311EEA: lea         rcx,[rbx+0000000000001350h]
  0000000140311EF1: call        0000000140412390
  0000000140311EF6: lea         rdx,[rbx+00000000000016F8h]
  0000000140311EFD: lea         rcx,[rbx+00000000000015C0h]
  0000000140311F04: call        0000000140412390
  0000000140311F09: mov         rax,qword ptr [rbx+0000000000001208h]
  0000000140311F10: mov         qword ptr [rbx+0000000000001200h],rax
  0000000140311F17: mov         eax,2
  0000000140311F1C: mov         word ptr [rbx+0000000000001728h],ax
  0000000140311F23: mov         qword ptr [rbx+0000000000001210h],rdi
  0000000140311F2A: cmp         dword ptr [000000014070FD18h],edi
  0000000140311F30: je          0000000140311F65
  0000000140311F32: cmp         dword ptr [rbx+0000000000001738h],edi
  0000000140311F38: je          0000000140311F57
  0000000140311F3A: movzx       r8d,byte ptr [00000001405C067Ah]
  0000000140311F42: lea         rdx,[rsp+28h]
  0000000140311F47: mov         r9d,0FF00h
  0000000140311F4D: mov         rcx,rbp
  0000000140311F50: call        0000000140422180
  0000000140311F55: jmp         0000000140311F65
  0000000140311F57: mov         byte ptr [rbx+0000000000000E20h],dil
  0000000140311F5E: mov         byte ptr [rbx+0000000000001090h],dil
  0000000140311F65: movzx       eax,byte ptr [00000001405ACEABh]
  0000000140311F6C: movzx       edx,word ptr [rsp+20h]
  0000000140311F71: mov         byte ptr [rbx+0000000000001758h],al
  0000000140311F77: mov         word ptr [rbx+000000000000172Ah],dx
  0000000140311F7E: cmp         dword ptr [000000014070FD18h],edi
  0000000140311F84: jne         0000000140311F97
  0000000140311F86: movzx       ecx,al
  0000000140311F89: cmp         dx,cx
  0000000140311F8C: jle         0000000140311F97
  0000000140311F8E: mov         r8,qword ptr [rbx+0000000000000CE8h]
  0000000140311F95: jmp         0000000140311F9E
  0000000140311F97: mov         r8,qword ptr [rbx+0000000000000CE0h]
  0000000140311F9E: mov         qword ptr [rbx+0000000000000CD8h],r8
  0000000140311FA5: mov         edi,11h
  0000000140311FAA: cmp         dword ptr [000000014070FD18h],0
  0000000140311FB1: je          0000000140311FEC
  0000000140311FB3: movsx       ecx,word ptr [rbx+000000000000172Ah]
  0000000140311FBA: movzx       eax,byte ptr [rbx+0000000000001758h]
  0000000140311FC1: cmp         ecx,eax
  0000000140311FC3: jle         0000000140311FEC
  0000000140311FC5: mov         eax,edi
  0000000140311FC7: sub         eax,ecx
  0000000140311FC9: and         eax,8000000Fh
  0000000140311FCE: jge         0000000140311FD7
  0000000140311FD0: dec         eax
  0000000140311FD2: or          eax,0FFFFFFF0h
  0000000140311FD5: inc         eax
  0000000140311FD7: movzx       ecx,word ptr [rbx+0000000000001728h]
  0000000140311FDE: cdq
  0000000140311FDF: sub         eax,edx
  0000000140311FE1: shl         cx,3
  0000000140311FE5: sar         eax,1
  0000000140311FE7: add         ax,cx
  0000000140311FEA: jmp         0000000140312006
  0000000140311FEC: movsx       eax,word ptr [rbx+000000000000172Ah]
  0000000140311FF3: cdq
  0000000140311FF4: sub         eax,edx
  0000000140311FF6: movzx       edx,word ptr [rbx+0000000000001728h]
  0000000140311FFD: shl         dx,3
  0000000140312001: sar         eax,1
  0000000140312003: add         ax,dx
  0000000140312006: movzx       edx,ax
  0000000140312009: mov         rcx,r8
  000000014031200C: call        0000000140412380
  0000000140312011: cmp         qword ptr [rbx+0000000000001200h],0
  0000000140312019: je          00000001403120A5
  000000014031201F: cmp         dword ptr [000000014070FD18h],0
  0000000140312026: jne         0000000140312041
  0000000140312028: movzx       eax,byte ptr [rbx+0000000000001758h]
  000000014031202F: cmp         word ptr [rbx+000000000000172Ah],ax
  0000000140312036: jle         0000000140312041
  0000000140312038: mov         rax,qword ptr [rbx+0000000000001210h]
  000000014031203F: jmp         0000000140312048
  0000000140312041: mov         rax,qword ptr [rbx+0000000000001208h]
  0000000140312048: mov         qword ptr [rbx+0000000000001200h],rax
  000000014031204F: cmp         dword ptr [000000014070FD18h],0
  0000000140312056: je          000000014031207F
  0000000140312058: movsx       eax,word ptr [rbx+000000000000172Ah]
  000000014031205F: movzx       ecx,byte ptr [rbx+0000000000001758h]
  0000000140312066: cmp         eax,ecx
  0000000140312068: jle         000000014031207F
  000000014031206A: sub         edi,eax
  000000014031206C: and         edi,8000000Fh
  0000000140312072: jge         000000014031207B
  0000000140312074: dec         edi
  0000000140312076: or          edi,0FFFFFFF0h
  0000000140312079: inc         edi
  000000014031207B: mov         eax,edi
  000000014031207D: jmp         0000000140312086
  000000014031207F: movsx       eax,word ptr [rbx+000000000000172Ah]
  0000000140312086: mov         rcx,qword ptr [rbx+0000000000001200h]
  000000014031208D: cdq
  000000014031208E: sub         eax,edx
  0000000140312090: movzx       edx,word ptr [rbx+0000000000001728h]
  0000000140312097: shl         dx,3
  000000014031209B: sar         eax,1
  000000014031209D: add         dx,ax
  00000001403120A0: call        0000000140412380
  00000001403120A5: mov         rax,rbx
  00000001403120A8: mov         rcx,qword ptr [rsp+38h]
  00000001403120AD: xor         rcx,rsp
  00000001403120B0: call        00000001404F77A0
  00000001403120B5: mov         rbx,qword ptr [rsp+0000000000000098h]
  00000001403120BD: add         rsp,40h
  00000001403120C1: pop         r15
  00000001403120C3: pop         r14
  00000001403120C5: pop         r13
  00000001403120C7: pop         r12
  00000001403120C9: pop         rdi
  00000001403120CA: pop         rsi
  00000001403120CB: pop         rbp
  00000001403120CC: ret
  00000001403120CD: int         3
  00000001403120CE: int         3
  00000001403120CF: int         3
  00000001403120D0: mov         qword ptr [rsp+20h],rbx
  00000001403120D5: push        rbp
  00000001403120D6: push        rsi
  00000001403120D7: push        rdi
  00000001403120D8: push        r12
  00000001403120DA: push        r13
  00000001403120DC: push        r14
  00000001403120DE: push        r15
  00000001403120E0: lea         rbp,[rsp-27h]
  00000001403120E5: sub         rsp,0B0h
  00000001403120EC: mov         rax,qword ptr [00000001406649D8h]
  00000001403120F3: xor         rax,rsp
  00000001403120F6: mov         qword ptr [rbp+1Fh],rax
  00000001403120FA: movzx       edi,dx
  00000001403120FD: mov         r12,r8
  0000000140312100: mov         word ptr [rbp-61h],di
  0000000140312104: mov         rbx,rcx
  0000000140312107: mov         word ptr [rbp-5Fh],r9w
  000000014031210C: call        00000001403074D0
  0000000140312111: lea         rax,[00000001405AA270h]
  0000000140312118: mov         qword ptr [rbx],rax
  000000014031211B: lea         r14,[rbx+0000000000000CD0h]
  0000000140312122: mov         rax,qword ptr [000000014065CB10h]
  0000000140312129: lea         rsi,[rbx+0000000000000D10h]
  0000000140312130: mov         qword ptr [r14],rax
  0000000140312133: mov         rcx,rsi
  0000000140312136: movzx       edx,word ptr [00000001405C067Ch]
  000000014031213D: call        0000000140421010
  0000000140312142: lea         r15,[rbx+0000000000000D58h]
  0000000140312149: mov         rcx,r15
  000000014031214C: call        0000000140410D80
  0000000140312151: lea         rcx,[rbx+0000000000000E78h]
  0000000140312158: call        0000000140410D80
  000000014031215D: lea         r13,[rbx+0000000000000F98h]
  0000000140312164: mov         rcx,r13
  0000000140312167: call        0000000140410D80
  000000014031216C: lea         rcx,[rbx+00000000000010B8h]
  0000000140312173: call        0000000140410D80
  0000000140312178: lea         rcx,[rbx+00000000000011D8h]
  000000014031217F: call        0000000140410D80
  0000000140312184: mov         rax,qword ptr [000000014065CB10h]
  000000014031218B: lea         rcx,[00000001405AB1F8h]
  0000000140312192: mov         byte ptr [rbx+22h],0FFh
  0000000140312196: xor         edx,edx
  0000000140312198: mov         qword ptr [rbx+00000000000012FCh],rdx
  000000014031219F: mov         dword ptr [rbx+0000000000000D50h],edx
  00000001403121A5: mov         dword ptr [rbx+0000000000000BA8h],edx
  00000001403121AB: mov         edx,edi
  00000001403121AD: mov         byte ptr [rbx+00000000000012F9h],1
  00000001403121B4: mov         dword ptr [rbx+30h],0A0000h
  00000001403121BB: mov         dword ptr [rbx+34h],0AFFF6h
  00000001403121C2: mov         dword ptr [rbx+38h],0FFF6h
  00000001403121C9: mov         dword ptr [rbx+3Ch],0FFF6FFF6h
  00000001403121D0: mov         dword ptr [rbx+40h],0FFF60000h
  00000001403121D7: mov         dword ptr [rbx+44h],0FFF6000Ah
  00000001403121DE: mov         dword ptr [rbx+48h],0Ah
  00000001403121E5: mov         dword ptr [rbx+4Ch],0A000Ah
  00000001403121EC: mov         qword ptr [rbp-69h],rax
  00000001403121F0: movzx       eax,byte ptr [00000001405ACE93h]
  00000001403121F7: mov         byte ptr [rbx+00000000000012F8h],al
  00000001403121FD: call        0000000140400170
  0000000140312202: mov         rdx,rax
  0000000140312205: lea         rcx,[rbp-11h]
  0000000140312209: call        00000001403FF7C0
  000000014031220E: mov         rcx,rbx
  0000000140312211: mov         rdx,qword ptr [rax]
  0000000140312214: call        0000000140340890
  0000000140312219: test        al,al
  000000014031221B: jne         00000001403128F4
  0000000140312221: mov         eax,edi
  0000000140312223: and         eax,0F00h
  0000000140312228: je          00000001403128C6
  000000014031222E: cmp         eax,100h
  0000000140312233: je          00000001403128BD
  0000000140312239: cmp         eax,200h
  000000014031223E: je          000000014031229B
  0000000140312240: cmp         eax,300h
  0000000140312245: jne         00000001403128F4
  000000014031224B: lea         rdx,[00000001405AC05Ch]
  0000000140312252: mov         word ptr [rbx+0Ah],0A0Ah
  0000000140312258: mov         rcx,r14
  000000014031225B: mov         dword ptr [rbx+24h],8
  0000000140312262: mov         byte ptr [rbx+00000000000005F0h],5
  0000000140312269: call        00000001403FD810
  000000014031226E: lea         rax,[00000001405AB538h]
  0000000140312275: mov         dword ptr [rbx+0000000000001300h],1
  000000014031227F: mov         qword ptr [rbx+28h],rax
  0000000140312283: mov         eax,9
  0000000140312288: mov         word ptr [rbx+00000000000005F2h],ax
  000000014031228F: mov         byte ptr [rbx+00000000000012F9h],4
  0000000140312296: jmp         00000001403128F4
  000000014031229B: lea         rax,[00000001405AB538h]
  00000001403122A2: mov         word ptr [rbx+0Ah],0E0Eh
  00000001403122A8: mov         qword ptr [rbx+28h],rax
  00000001403122AC: and         edi,0Fh
  00000001403122AF: mov         dword ptr [rbx+24h],8
  00000001403122B6: mov         eax,9
  00000001403122BB: mov         word ptr [rbx+00000000000005F2h],ax
  00000001403122C2: mov         byte ptr [rbx+00000000000012F9h],al
  00000001403122C8: mov         byte ptr [rbx+00000000000005F0h],0Dh
  00000001403122CF: mov         dword ptr [rbx+0000000000001300h],1
  00000001403122D9: cmp         edi,8
  00000001403122DC: ja          00000001403128F4
  00000001403122E2: lea         rdx,[0000000140000000h]
  00000001403122E9: movsxd      rax,edi
  00000001403122EC: mov         ecx,dword ptr [rdx+rax*4+0000000000312EBCh]
  00000001403122F3: add         rcx,rdx
  00000001403122F6: jmp         rcx
  00000001403122F8: lea         rdx,[00000001405ABE48h]
  00000001403122FF: 49
  0000000140312300: 8B

  Summary

      589000 .text
