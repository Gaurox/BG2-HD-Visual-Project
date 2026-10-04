Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  0000000140333CB0: mov         qword ptr [rsp+8],rbx
  0000000140333CB5: mov         qword ptr [rsp+10h],rbp
  0000000140333CBA: mov         qword ptr [rsp+18h],rsi
  0000000140333CBF: push        rdi
  0000000140333CC0: push        r12
  0000000140333CC2: push        r13
  0000000140333CC4: push        r14
  0000000140333CC6: push        r15
  0000000140333CC8: sub         rsp,30h
  0000000140333CCC: movzx       eax,r8b
  0000000140333CD0: mov         esi,r9d
  0000000140333CD3: movzx       ebp,dl
  0000000140333CD6: mov         rdi,rcx
  0000000140333CD9: and         eax,0F0h
  0000000140333CDE: je          0000000140333DD1
  0000000140333CE4: cmp         eax,10h
  0000000140333CE7: jne         0000000140333EA2
  0000000140333CED: cmp         qword ptr [rcx+0000000000001200h],0
  0000000140333CF5: je          0000000140333EA2
  0000000140333CFB: movzx       r12d,byte ptr [rsp+0000000000000080h]
  0000000140333D04: and         r8b,0Fh
  0000000140333D08: movzx       ebx,r8b
  0000000140333D0C: add         rcx,1218h
  0000000140333D13: movzx       r15d,dl
  0000000140333D17: movzx       r8d,bx
  0000000140333D1B: movzx       edx,r15w
  0000000140333D1F: mov         byte ptr [rsp+20h],r12b
  0000000140333D24: call        0000000140411330
  0000000140333D29: mov         r9d,esi
  0000000140333D2C: mov         byte ptr [rsp+20h],r12b
  0000000140333D31: movzx       r8d,bx
  0000000140333D35: lea         rcx,[rdi+0000000000001488h]
  0000000140333D3C: movzx       edx,r15w
  0000000140333D40: call        0000000140411330
  0000000140333D45: test        bpl,bpl
  0000000140333D48: je          0000000140333D68
  0000000140333D4A: movzx       edx,bx
  0000000140333D4D: lea         rcx,[rdi+0000000000001218h]
  0000000140333D54: call        00000001404126A0
  0000000140333D59: movzx       edx,bx
  0000000140333D5C: lea         rcx,[rdi+0000000000001488h]
  0000000140333D63: call        00000001404126A0
  0000000140333D68: cmp         dword ptr [000000014070FD18h],0
  0000000140333D6F: jne         0000000140333EA2
  0000000140333D75: mov         r9d,esi
  0000000140333D78: mov         byte ptr [rsp+20h],r12b
  0000000140333D7D: movzx       r8d,bx
  0000000140333D81: lea         rcx,[rdi+0000000000001350h]
  0000000140333D88: movzx       edx,r15w
  0000000140333D8C: call        0000000140411330
  0000000140333D91: mov         r9d,esi
  0000000140333D94: mov         byte ptr [rsp+20h],r12b
  0000000140333D99: movzx       r8d,bx
  0000000140333D9D: lea         rcx,[rdi+00000000000015C0h]
  0000000140333DA4: movzx       edx,r15w
  0000000140333DA8: call        0000000140411330
  0000000140333DAD: test        bpl,bpl
  0000000140333DB0: je          0000000140333EA2
  0000000140333DB6: movzx       edx,bx
  0000000140333DB9: lea         rcx,[rdi+0000000000001350h]
  0000000140333DC0: call        00000001404126A0
  0000000140333DC5: lea         rcx,[rdi+00000000000015C0h]
  0000000140333DCC: jmp         0000000140333E9A
  0000000140333DD1: movzx       r12d,byte ptr [rsp+0000000000000080h]
  0000000140333DDA: and         r8b,0Fh
  0000000140333DDE: movzx       ebx,r8b
  0000000140333DE2: add         rcx,0CF0h
  0000000140333DE9: movzx       r15d,bpl
  0000000140333DED: movzx       r8d,bx
  0000000140333DF1: movzx       edx,r15w
  0000000140333DF5: mov         byte ptr [rsp+20h],r12b
  0000000140333DFA: call        0000000140411330
  0000000140333DFF: mov         r9d,esi
  0000000140333E02: mov         byte ptr [rsp+20h],r12b
  0000000140333E07: movzx       r8d,bx
  0000000140333E0B: lea         rcx,[rdi+0000000000000F60h]
  0000000140333E12: movzx       edx,r15w
  0000000140333E16: call        0000000140411330
  0000000140333E1B: test        bpl,bpl
  0000000140333E1E: je          0000000140333E3E
  0000000140333E20: movzx       edx,bx
  0000000140333E23: lea         rcx,[rdi+0000000000000CF0h]
  0000000140333E2A: call        00000001404126A0
  0000000140333E2F: movzx       edx,bx
  0000000140333E32: lea         rcx,[rdi+0000000000000F60h]
  0000000140333E39: call        00000001404126A0
  0000000140333E3E: cmp         dword ptr [000000014070FD18h],0
  0000000140333E45: jne         0000000140333EA2
  0000000140333E47: mov         r9d,esi
  0000000140333E4A: mov         byte ptr [rsp+20h],r12b
  0000000140333E4F: movzx       r8d,bx
  0000000140333E53: lea         rcx,[rdi+0000000000000E28h]
  0000000140333E5A: movzx       edx,r15w
  0000000140333E5E: call        0000000140411330
  0000000140333E63: mov         r9d,esi
  0000000140333E66: mov         byte ptr [rsp+20h],r12b
  0000000140333E6B: movzx       r8d,bx
  0000000140333E6F: lea         rcx,[rdi+0000000000001098h]
  0000000140333E76: movzx       edx,r15w
  0000000140333E7A: call        0000000140411330
  0000000140333E7F: test        bpl,bpl
  0000000140333E82: je          0000000140333EA2
  0000000140333E84: movzx       edx,bx
  0000000140333E87: lea         rcx,[rdi+0000000000000E28h]
  0000000140333E8E: call        00000001404126A0
  0000000140333E93: lea         rcx,[rdi+0000000000001098h]
  0000000140333E9A: movzx       edx,bx
  0000000140333E9D: call        00000001404126A0
  0000000140333EA2: mov         rbx,qword ptr [rsp+60h]
  0000000140333EA7: mov         rbp,qword ptr [rsp+68h]
  0000000140333EAC: mov         rsi,qword ptr [rsp+70h]
  0000000140333EB1: add         rsp,30h
  0000000140333EB5: pop         r15
  0000000140333EB7: pop         r14
  0000000140333EB9: pop         r13
  0000000140333EBB: pop         r12
  0000000140333EBD: pop         rdi
  0000000140333EBE: ret
  0000000140333EBF: int         3
  0000000140333EC0: mov         qword ptr [rsp+8],rbx
  0000000140333EC5: mov         qword ptr [rsp+10h],rbp
  0000000140333ECA: mov         qword ptr [rsp+18h],rsi
  0000000140333ECF: push        rdi
  0000000140333ED0: push        r12
  0000000140333ED2: push        r13
  0000000140333ED4: push        r14
  0000000140333ED6: push        r15
  0000000140333ED8: sub         rsp,30h
  0000000140333EDC: movzx       eax,r8b
  0000000140333EE0: mov         ebp,r9d
  0000000140333EE3: movzx       ebx,dl
  0000000140333EE6: mov         rsi,rcx
  0000000140333EE9: and         eax,0F0h
  0000000140333EEE: je          00000001403340E9
  0000000140333EF4: cmp         eax,10h
  0000000140333EF7: jne         00000001403342C5
  0000000140333EFD: cmp         qword ptr [rcx+0000000000001200h],0
  0000000140333F05: je          00000001403342C5
  0000000140333F0B: cmp         dword ptr [rcx+0000000000001738h],0
  0000000140333F12: je          0000000140333FEF
  0000000140333F18: movzx       r12d,byte ptr [rsp+0000000000000080h]
  0000000140333F21: and         r8b,0Fh
  0000000140333F25: movzx       edi,r8b
  0000000140333F29: add         rcx,1218h
  0000000140333F30: movzx       r15d,dl
  0000000140333F34: movzx       r8d,di
  0000000140333F38: movzx       edx,r15w
  0000000140333F3C: mov         byte ptr [rsp+20h],r12b
  0000000140333F41: call        0000000140411330
  0000000140333F46: mov         r9d,ebp
  0000000140333F49: mov         byte ptr [rsp+20h],r12b
  0000000140333F4E: movzx       r8d,di
  0000000140333F52: lea         rcx,[rsi+0000000000001488h]
  0000000140333F59: movzx       edx,r15w
  0000000140333F5D: call        0000000140411330
  0000000140333F62: test        bl,bl
  0000000140333F64: je          0000000140333F84
  0000000140333F66: movzx       edx,di
  0000000140333F69: lea         rcx,[rsi+0000000000001218h]
  0000000140333F70: call        00000001404126A0
  0000000140333F75: movzx       edx,di
  0000000140333F78: lea         rcx,[rsi+0000000000001488h]
  0000000140333F7F: call        00000001404126A0
  0000000140333F84: cmp         dword ptr [000000014070FD18h],0
  0000000140333F8B: jne         00000001403342C5
  0000000140333F91: mov         r9d,ebp
  0000000140333F94: mov         byte ptr [rsp+20h],r12b
  0000000140333F99: movzx       r8d,di
  0000000140333F9D: lea         rcx,[rsi+0000000000001350h]
  0000000140333FA4: movzx       edx,r15w
  0000000140333FA8: call        0000000140411330
  0000000140333FAD: mov         r9d,ebp
  0000000140333FB0: mov         byte ptr [rsp+20h],r12b
  0000000140333FB5: movzx       r8d,di
  0000000140333FB9: lea         rcx,[rsi+00000000000015C0h]
  0000000140333FC0: movzx       edx,r15w
  0000000140333FC4: call        0000000140411330
  0000000140333FC9: test        bl,bl
  0000000140333FCB: je          00000001403342C5
  0000000140333FD1: movzx       edx,di
  0000000140333FD4: lea         rcx,[rsi+0000000000001350h]
  0000000140333FDB: call        00000001404126A0
  0000000140333FE0: movzx       edx,di
  0000000140333FE3: lea         rcx,[rsi+00000000000015C0h]
  0000000140333FEA: jmp         00000001403342C0
  0000000140333FEF: test        bl,bl
  0000000140333FF1: jne         000000014033403D
  0000000140333FF3: add         rcx,1220h
  0000000140333FFA: mov         edx,ebp
  0000000140333FFC: call        0000000140412690
  0000000140334001: lea         rcx,[rsi+0000000000001490h]
  0000000140334008: mov         edx,ebp
  000000014033400A: call        0000000140412690
  000000014033400F: cmp         dword ptr [000000014070FD18h],0
  0000000140334016: jne         00000001403342C5
  000000014033401C: lea         rcx,[rsi+0000000000001358h]
  0000000140334023: mov         edx,ebp
  0000000140334025: call        0000000140412690
  000000014033402A: lea         rcx,[rsi+00000000000015C8h]
  0000000140334031: mov         edx,ebp
  0000000140334033: call        0000000140412690
  0000000140334038: jmp         00000001403342C5
  000000014033403D: movzx       r15d,byte ptr [rsp+0000000000000080h]
  0000000140334046: mov         r8d,ebp
  0000000140334049: movzx       r14d,bl
  000000014033404D: movzx       r9d,r15b
  0000000140334051: movzx       edx,r14w
  0000000140334055: add         rcx,1218h
  000000014033405C: call        0000000140411420
  0000000140334061: movzx       r9d,r15b
  0000000140334065: lea         rcx,[rsi+0000000000001488h]
  000000014033406C: mov         r8d,ebp
  000000014033406F: movzx       edx,r14w
  0000000140334073: call        0000000140411420
  0000000140334078: xor         edx,edx
  000000014033407A: lea         rcx,[rsi+0000000000001218h]
  0000000140334081: call        00000001404126A0
  0000000140334086: xor         edx,edx
  0000000140334088: lea         rcx,[rsi+0000000000001488h]
  000000014033408F: call        00000001404126A0
  0000000140334094: cmp         dword ptr [000000014070FD18h],0
  000000014033409B: jne         00000001403342C5
  00000001403340A1: movzx       r9d,r15b
  00000001403340A5: lea         rcx,[rsi+0000000000001350h]
  00000001403340AC: mov         r8d,ebp
  00000001403340AF: movzx       edx,r14w
  00000001403340B3: call        0000000140411420
  00000001403340B8: movzx       r9d,r15b
  00000001403340BC: lea         rcx,[rsi+00000000000015C0h]
  00000001403340C3: mov         r8d,ebp
  00000001403340C6: movzx       edx,r14w
  00000001403340CA: call        0000000140411420
  00000001403340CF: xor         edx,edx
  00000001403340D1: lea         rcx,[rsi+0000000000001350h]
  00000001403340D8: call        00000001404126A0
  00000001403340DD: lea         rcx,[rsi+00000000000015C0h]
  00000001403340E4: jmp         00000001403342BE
  00000001403340E9: cmp         dword ptr [rcx+0000000000001738h],0
  00000001403340F0: je          00000001403341CD
  00000001403340F6: movzx       r12d,byte ptr [rsp+0000000000000080h]
  00000001403340FF: and         r8b,0Fh
  0000000140334103: movzx       edi,r8b
  0000000140334107: add         rcx,0CF0h
  000000014033410E: movzx       r15d,bl
  0000000140334112: movzx       r8d,di
  0000000140334116: movzx       edx,r15w
  000000014033411A: mov         byte ptr [rsp+20h],r12b
  000000014033411F: call        0000000140411330
  0000000140334124: mov         r9d,ebp
  0000000140334127: mov         byte ptr [rsp+20h],r12b
  000000014033412C: movzx       r8d,di
  0000000140334130: lea         rcx,[rsi+0000000000000F60h]
  0000000140334137: movzx       edx,r15w
  000000014033413B: call        0000000140411330
  0000000140334140: test        bl,bl
  0000000140334142: je          0000000140334162
  0000000140334144: movzx       edx,di
  0000000140334147: lea         rcx,[rsi+0000000000000CF0h]
  000000014033414E: call        00000001404126A0
  0000000140334153: movzx       edx,di
  0000000140334156: lea         rcx,[rsi+0000000000000F60h]
  000000014033415D: call        00000001404126A0
  0000000140334162: cmp         dword ptr [000000014070FD18h],0
  0000000140334169: jne         00000001403342C5
  000000014033416F: mov         r9d,ebp
  0000000140334172: mov         byte ptr [rsp+20h],r12b
  0000000140334177: movzx       r8d,di
  000000014033417B: lea         rcx,[rsi+0000000000000E28h]
  0000000140334182: movzx       edx,r15w
  0000000140334186: call        0000000140411330
  000000014033418B: mov         r9d,ebp
  000000014033418E: mov         byte ptr [rsp+20h],r12b
  0000000140334193: movzx       r8d,di
  0000000140334197: lea         rcx,[rsi+0000000000001098h]
  000000014033419E: movzx       edx,r15w
  00000001403341A2: call        0000000140411330
  00000001403341A7: test        bl,bl
  00000001403341A9: je          00000001403342C5
  00000001403341AF: movzx       edx,di
  00000001403341B2: lea         rcx,[rsi+0000000000000E28h]
  00000001403341B9: call        00000001404126A0
  00000001403341BE: movzx       edx,di
  00000001403341C1: lea         rcx,[rsi+0000000000001098h]
  00000001403341C8: jmp         00000001403342C0
  00000001403341CD: test        bl,bl
  00000001403341CF: jne         000000014033421B
  00000001403341D1: add         rcx,0CF8h
  00000001403341D8: mov         edx,ebp
  00000001403341DA: call        0000000140412690
  00000001403341DF: lea         rcx,[rsi+0000000000000F68h]
  00000001403341E6: mov         edx,ebp
  00000001403341E8: call        0000000140412690
  00000001403341ED: cmp         dword ptr [000000014070FD18h],0
  00000001403341F4: jne         00000001403342C5
  00000001403341FA: lea         rcx,[rsi+0000000000000E30h]
  0000000140334201: mov         edx,ebp
  0000000140334203: call        0000000140412690
  0000000140334208: lea         rcx,[rsi+00000000000010A0h]
  000000014033420F: mov         edx,ebp
  0000000140334211: call        0000000140412690
  0000000140334216: jmp         00000001403342C5
  000000014033421B: movzx       r15d,byte ptr [rsp+0000000000000080h]
  0000000140334224: mov         r8d,ebp
  0000000140334227: movzx       r14d,bl
  000000014033422B: movzx       r9d,r15b
  000000014033422F: movzx       edx,r14w
  0000000140334233: add         rcx,0CF0h
  000000014033423A: call        0000000140411420
  000000014033423F: movzx       r9d,r15b
  0000000140334243: lea         rcx,[rsi+0000000000000F60h]
  000000014033424A: mov         r8d,ebp
  000000014033424D: movzx       edx,r14w
  0000000140334251: call        0000000140411420
  0000000140334256: xor         edx,edx
  0000000140334258: lea         rcx,[rsi+0000000000000CF0h]
  000000014033425F: call        00000001404126A0
  0000000140334264: xor         edx,edx
  0000000140334266: lea         rcx,[rsi+0000000000000F60h]
  000000014033426D: call        00000001404126A0
  0000000140334272: cmp         dword ptr [000000014070FD18h],0
  0000000140334279: jne         00000001403342C5
  000000014033427B: movzx       r9d,r15b
  000000014033427F: lea         rcx,[rsi+0000000000000E28h]
  0000000140334286: mov         r8d,ebp
  0000000140334289: movzx       edx,r14w
  000000014033428D: call        0000000140411420
  0000000140334292: movzx       r9d,r15b
  0000000140334296: lea         rcx,[rsi+0000000000001098h]
  000000014033429D: mov         r8d,ebp
  00000001403342A0: movzx       edx,r14w
  00000001403342A4: call        0000000140411420
  00000001403342A9: xor         edx,edx
  00000001403342AB: lea         rcx,[rsi+0000000000000E28h]
  00000001403342B2: call        00000001404126A0
  00000001403342B7: lea         rcx,[rsi+0000000000001098h]
  00000001403342BE: xor         edx,edx
  00000001403342C0: call        00000001404126A0
  00000001403342C5: mov         rbx,qword ptr [rsp+60h]
  00000001403342CA: mov         rbp,qword ptr [rsp+68h]
  00000001403342CF: mov         rsi,qword ptr [rsp+70h]
  00000001403342D4: add         rsp,30h
  00000001403342D8: pop         r15
  00000001403342DA: pop         r14
  00000001403342DC: pop         r13
  00000001403342DE: pop         r12
  00000001403342E0: pop         rdi
  00000001403342E1: ret
  00000001403342E2: int         3
  00000001403342E3: int         3
  00000001403342E4: int         3
  00000001403342E5: int         3
  00000001403342E6: int         3
  00000001403342E7: int         3
  00000001403342E8: int         3
  00000001403342E9: int         3
  00000001403342EA: int         3
  00000001403342EB: int         3
  00000001403342EC: int         3
  00000001403342ED: int         3
  00000001403342EE: int         3
  00000001403342EF: int         3
  00000001403342F0: test        r8b,0F0h
  00000001403342F4: jne         0000000140334679
  00000001403342FA: mov         byte ptr [rsp+10h],dl
  00000001403342FE: push        rbx
  00000001403342FF: push        rsi
  0000000140334300: push        r13
  0000000140334302: sub         rsp,40h
  0000000140334306: cmp         dword ptr [rcx+0000000000000D50h],0
  000000014033430D: mov         esi,r9d
  0000000140334310: movzx       eax,byte ptr [rcx+00000000000012F9h]
  0000000140334317: movzx       r13d,r8b
  000000014033431B: mov         qword ptr [rsp+60h],rbp
  0000000140334320: mov         rbx,rcx
  0000000140334323: mov         qword ptr [rsp+70h],rdi
  0000000140334328: mov         qword ptr [rsp+38h],r14
  000000014033432D: mov         qword ptr [rsp+30h],r15
  0000000140334332: je          00000001403344B6
  0000000140334338: mov         qword ptr [rsp+78h],r12
  000000014033433D: xor         r12b,r12b
  0000000140334340: test        al,al
  0000000140334342: je          000000014033441F
  0000000140334348: movzx       r15d,byte ptr [rsp+0000000000000080h]
  0000000140334351: movzx       eax,r8b
  0000000140334355: and         al,0Fh
  0000000140334357: movzx       r14d,dl
  000000014033435B: movzx       ebp,al
  000000014033435E: xchg        ax,ax
  0000000140334360: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334367: mov         r9d,esi
  000000014033436A: movzx       eax,r12b
  000000014033436E: movzx       r8d,bp
  0000000140334372: imul        rdi,rax,138h
  0000000140334379: movzx       edx,r14w
  000000014033437D: mov         byte ptr [rsp+20h],r15b
  0000000140334382: add         rcx,rdi
  0000000140334385: call        0000000140411330
  000000014033438A: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334391: mov         r9d,esi
  0000000140334394: add         rcx,rdi
  0000000140334397: mov         byte ptr [rsp+20h],r15b
  000000014033439C: movzx       r8d,bp
  00000001403343A0: movzx       edx,r14w
  00000001403343A4: call        0000000140411330
  00000001403343A9: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  00000001403343B0: mov         r9d,esi
  00000001403343B3: add         rcx,rdi
  00000001403343B6: mov         byte ptr [rsp+20h],r15b
  00000001403343BB: movzx       r8d,bp
  00000001403343BF: movzx       edx,r14w
  00000001403343C3: call        0000000140411330
  00000001403343C8: mov         rcx,qword ptr [rbx+0000000000000D00h]
  00000001403343CF: mov         r9d,esi
  00000001403343D2: add         rcx,rdi
  00000001403343D5: mov         byte ptr [rsp+20h],r15b
  00000001403343DA: movzx       r8d,bp
  00000001403343DE: movzx       edx,r14w
  00000001403343E2: call        0000000140411330
  00000001403343E7: mov         rax,qword ptr [rbx+0000000000000D08h]
  00000001403343EE: mov         r9d,esi
  00000001403343F1: movzx       r8d,bp
  00000001403343F5: mov         byte ptr [rsp+20h],r15b
  00000001403343FA: movzx       edx,r14w
  00000001403343FE: lea         rcx,[rdi+rax]
  0000000140334402: call        0000000140411330
  0000000140334407: movzx       eax,byte ptr [rbx+00000000000012F9h]
  000000014033440E: inc         r12b
  0000000140334411: cmp         r12b,al
  0000000140334414: jb          0000000140334360
  000000014033441A: movzx       edx,byte ptr [rsp+68h]
  000000014033441F: mov         r12,qword ptr [rsp+78h]
  0000000140334424: test        dl,dl
  0000000140334426: je          000000014033465D
  000000014033442C: xor         bpl,bpl
  000000014033442F: test        al,al
  0000000140334431: je          000000014033465D
  0000000140334437: and         r13b,0Fh
  000000014033443B: movzx       esi,r13b
  000000014033443F: nop
  0000000140334440: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334447: movzx       edx,si
  000000014033444A: movzx       eax,bpl
  000000014033444E: imul        rdi,rax,138h
  0000000140334455: add         rcx,rdi
  0000000140334458: call        00000001404126A0
  000000014033445D: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334464: movzx       edx,si
  0000000140334467: add         rcx,rdi
  000000014033446A: call        00000001404126A0
  000000014033446F: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  0000000140334476: movzx       edx,si
  0000000140334479: add         rcx,rdi
  000000014033447C: call        00000001404126A0
  0000000140334481: mov         rcx,qword ptr [rbx+0000000000000D00h]
  0000000140334488: movzx       edx,si
  000000014033448B: add         rcx,rdi
  000000014033448E: call        00000001404126A0
  0000000140334493: mov         rcx,qword ptr [rbx+0000000000000D08h]
  000000014033449A: movzx       edx,si
  000000014033449D: add         rcx,rdi
  00000001403344A0: call        00000001404126A0
  00000001403344A5: inc         bpl
  00000001403344A8: cmp         bpl,byte ptr [rbx+00000000000012F9h]
  00000001403344AF: jb          0000000140334440
  00000001403344B1: jmp         000000014033465D
  00000001403344B6: test        dl,dl
  00000001403344B8: jne         0000000140334555
  00000001403344BE: xor         bpl,bpl
  00000001403344C1: test        al,al
  00000001403344C3: je          000000014033465D
  00000001403344C9: nop         dword ptr [rax+0000000000000000h]
  00000001403344D0: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  00000001403344D7: mov         edx,esi
  00000001403344D9: movzx       eax,bpl
  00000001403344DD: add         rcx,8
  00000001403344E1: imul        rdi,rax,138h
  00000001403344E8: add         rcx,rdi
  00000001403344EB: call        0000000140412690
  00000001403344F0: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  00000001403344F7: mov         edx,esi
  00000001403344F9: add         rcx,8
  00000001403344FD: add         rcx,rdi
  0000000140334500: call        0000000140412690
  0000000140334505: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  000000014033450C: mov         edx,esi
  000000014033450E: add         rcx,8
  0000000140334512: add         rcx,rdi
  0000000140334515: call        0000000140412690
  000000014033451A: mov         rcx,qword ptr [rbx+0000000000000D00h]
  0000000140334521: mov         edx,esi
  0000000140334523: add         rcx,8
  0000000140334527: add         rcx,rdi
  000000014033452A: call        0000000140412690
  000000014033452F: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140334536: mov         edx,esi
  0000000140334538: add         rcx,8
  000000014033453C: add         rcx,rdi
  000000014033453F: call        0000000140412690
  0000000140334544: inc         bpl
  0000000140334547: cmp         bpl,byte ptr [rbx+00000000000012F9h]
  000000014033454E: jb          00000001403344D0
  0000000140334550: jmp         000000014033465D
  0000000140334555: xor         r15b,r15b
  0000000140334558: test        al,al
  000000014033455A: je          000000014033465D
  0000000140334560: movzx       r14d,byte ptr [rsp+0000000000000080h]
  0000000140334569: movzx       ebp,dl
  000000014033456C: nop         dword ptr [rax]
  0000000140334570: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334577: movzx       r9d,r14b
  000000014033457B: movzx       eax,r15b
  000000014033457F: mov         r8d,esi
  0000000140334582: imul        rdi,rax,138h
  0000000140334589: movzx       edx,bp
  000000014033458C: add         rcx,rdi
  000000014033458F: call        0000000140411420
  0000000140334594: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  000000014033459B: movzx       r9d,r14b
  000000014033459F: add         rcx,rdi
  00000001403345A2: mov         r8d,esi
  00000001403345A5: movzx       edx,bp
  00000001403345A8: call        0000000140411420
  00000001403345AD: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  00000001403345B4: movzx       r9d,r14b
  00000001403345B8: add         rcx,rdi
  00000001403345BB: mov         r8d,esi
  00000001403345BE: movzx       edx,bp
  00000001403345C1: call        0000000140411420
  00000001403345C6: mov         rcx,qword ptr [rbx+0000000000000D00h]
  00000001403345CD: movzx       r9d,r14b
  00000001403345D1: add         rcx,rdi
  00000001403345D4: mov         r8d,esi
  00000001403345D7: movzx       edx,bp
  00000001403345DA: call        0000000140411420
  00000001403345DF: mov         rcx,qword ptr [rbx+0000000000000D08h]
  00000001403345E6: movzx       r9d,r14b
  00000001403345EA: add         rcx,rdi
  00000001403345ED: mov         r8d,esi
  00000001403345F0: movzx       edx,bp
  00000001403345F3: call        0000000140411420
  00000001403345F8: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  00000001403345FF: xor         edx,edx
  0000000140334601: add         rcx,rdi
  0000000140334604: call        00000001404126A0
  0000000140334609: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334610: xor         edx,edx
  0000000140334612: add         rcx,rdi
  0000000140334615: call        00000001404126A0
  000000014033461A: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  0000000140334621: xor         edx,edx
  0000000140334623: add         rcx,rdi
  0000000140334626: call        00000001404126A0
  000000014033462B: mov         rcx,qword ptr [rbx+0000000000000D00h]
  0000000140334632: xor         edx,edx
  0000000140334634: add         rcx,rdi
  0000000140334637: call        00000001404126A0
  000000014033463C: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140334643: xor         edx,edx
  0000000140334645: add         rcx,rdi
  0000000140334648: call        00000001404126A0
  000000014033464D: inc         r15b
  0000000140334650: cmp         r15b,byte ptr [rbx+00000000000012F9h]
  0000000140334657: jb          0000000140334570
  000000014033465D: mov         r14,qword ptr [rsp+38h]
  0000000140334662: mov         rdi,qword ptr [rsp+70h]
  0000000140334667: mov         rbp,qword ptr [rsp+60h]
  000000014033466C: mov         r15,qword ptr [rsp+30h]
  0000000140334671: add         rsp,40h
  0000000140334675: pop         r13
  0000000140334677: pop         rsi
  0000000140334678: pop         rbx
  0000000140334679: ret
  000000014033467A: int         3
  000000014033467B: int         3
  000000014033467C: int         3
  000000014033467D: int         3
  000000014033467E: int         3
  000000014033467F: int         3
  0000000140334680: test        r8b,0F0h
  0000000140334684: jne         0000000140334874
  000000014033468A: push        rbx
  000000014033468B: push        rbp
  000000014033468C: push        r15
  000000014033468E: sub         rsp,40h
  0000000140334692: cmp         dword ptr [rcx+0000000000000D30h],0
  0000000140334699: mov         ebp,r9d
  000000014033469C: movzx       eax,byte ptr [rcx+0000000000000D35h]
  00000001403346A3: movzx       r15d,dl
  00000001403346A7: mov         qword ptr [rsp+60h],rsi
  00000001403346AC: mov         rbx,rcx
  00000001403346AF: mov         qword ptr [rsp+68h],rdi
  00000001403346B4: mov         qword ptr [rsp+30h],r14
  00000001403346B9: je          000000014033477F
  00000001403346BF: xor         dil,dil
  00000001403346C2: test        al,al
  00000001403346C4: je          000000014033485D
  00000001403346CA: mov         qword ptr [rsp+70h],r12
  00000001403346CF: and         r8b,0Fh
  00000001403346D3: mov         qword ptr [rsp+38h],r13
  00000001403346D8: movzx       r13d,byte ptr [rsp+0000000000000080h]
  00000001403346E1: movzx       r14d,r8b
  00000001403346E5: movzx       r12d,dl
  00000001403346E9: nop         dword ptr [rax+0000000000000000h]
  00000001403346F0: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  00000001403346F7: mov         r9d,ebp
  00000001403346FA: movzx       eax,dil
  00000001403346FE: movzx       r8d,r14w
  0000000140334702: imul        rsi,rax,138h
  0000000140334709: movzx       edx,r12w
  000000014033470D: mov         byte ptr [rsp+20h],r13b
  0000000140334712: add         rcx,rsi
  0000000140334715: call        0000000140411330
  000000014033471A: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334721: mov         r9d,ebp
  0000000140334724: add         rcx,rsi
  0000000140334727: mov         byte ptr [rsp+20h],r13b
  000000014033472C: movzx       r8d,r14w
  0000000140334730: movzx       edx,r12w
  0000000140334734: call        0000000140411330
  0000000140334739: test        r15b,r15b
  000000014033473C: je          0000000140334764
  000000014033473E: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334745: movzx       edx,r14w
  0000000140334749: add         rcx,rsi
  000000014033474C: call        00000001404126A0
  0000000140334751: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334758: movzx       edx,r14w
  000000014033475C: add         rcx,rsi
  000000014033475F: call        00000001404126A0
  0000000140334764: inc         dil
  0000000140334767: cmp         dil,byte ptr [rbx+0000000000000D35h]
  000000014033476E: jb          00000001403346F0
  0000000140334770: mov         r13,qword ptr [rsp+38h]
  0000000140334775: mov         r12,qword ptr [rsp+70h]
  000000014033477A: jmp         000000014033485D
  000000014033477F: xor         sil,sil
  0000000140334782: test        r15b,r15b
  0000000140334785: jne         00000001403347D6
  0000000140334787: test        al,al
  0000000140334789: je          000000014033485D
  000000014033478F: nop
  0000000140334790: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334797: mov         edx,ebp
  0000000140334799: movzx       eax,sil
  000000014033479D: add         rcx,8
  00000001403347A1: imul        rdi,rax,138h
  00000001403347A8: add         rcx,rdi
  00000001403347AB: call        0000000140412690
  00000001403347B0: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  00000001403347B7: mov         edx,ebp
  00000001403347B9: add         rcx,8
  00000001403347BD: add         rcx,rdi
  00000001403347C0: E8

  Summary

      589000 .text
