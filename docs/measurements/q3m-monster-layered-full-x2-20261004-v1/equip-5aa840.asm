Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  00000001403347C0: call        0000000140412690
  00000001403347C5: inc         sil
  00000001403347C8: cmp         sil,byte ptr [rbx+0000000000000D35h]
  00000001403347CF: jb          0000000140334790
  00000001403347D1: jmp         000000014033485D
  00000001403347D6: test        al,al
  00000001403347D8: je          000000014033485D
  00000001403347DE: movzx       r14d,r15b
  00000001403347E2: movzx       r15d,byte ptr [rsp+0000000000000080h]
  00000001403347EB: nop         dword ptr [rax+rax]
  00000001403347F0: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  00000001403347F7: movzx       r9d,r15b
  00000001403347FB: movzx       eax,sil
  00000001403347FF: mov         r8d,ebp
  0000000140334802: imul        rdi,rax,138h
  0000000140334809: movzx       edx,r14w
  000000014033480D: add         rcx,rdi
  0000000140334810: call        0000000140411420
  0000000140334815: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  000000014033481C: movzx       r9d,r15b
  0000000140334820: add         rcx,rdi
  0000000140334823: mov         r8d,ebp
  0000000140334826: movzx       edx,r14w
  000000014033482A: call        0000000140411420
  000000014033482F: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334836: xor         edx,edx
  0000000140334838: add         rcx,rdi
  000000014033483B: call        00000001404126A0
  0000000140334840: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334847: xor         edx,edx
  0000000140334849: add         rcx,rdi
  000000014033484C: call        00000001404126A0
  0000000140334851: inc         sil
  0000000140334854: cmp         sil,byte ptr [rbx+0000000000000D35h]
  000000014033485B: jb          00000001403347F0
  000000014033485D: mov         rdi,qword ptr [rsp+68h]
  0000000140334862: mov         rsi,qword ptr [rsp+60h]
  0000000140334867: mov         r14,qword ptr [rsp+30h]
  000000014033486C: add         rsp,40h
  0000000140334870: pop         r15
  0000000140334872: pop         rbp
  0000000140334873: pop         rbx
  0000000140334874: ret
  0000000140334875: int         3
  0000000140334876: int         3
  0000000140334877: int         3
  0000000140334878: int         3
  0000000140334879: int         3
  000000014033487A: int         3
  000000014033487B: int         3
  000000014033487C: int         3
  000000014033487D: int         3
  000000014033487E: int         3
  000000014033487F: int         3
  0000000140334880: test        r8b,0F0h
  0000000140334884: jne         00000001403349B1
  000000014033488A: push        rbp
  000000014033488B: push        rsi
  000000014033488C: push        rdi
  000000014033488D: sub         rsp,40h
  0000000140334891: cmp         dword ptr [rcx+0000000000001204h],0
  0000000140334898: mov         ebp,r9d
  000000014033489B: mov         qword ptr [rsp+60h],rbx
  00000001403348A0: movzx       edi,dl
  00000001403348A3: mov         qword ptr [rsp+38h],r14
  00000001403348A8: mov         rsi,rcx
  00000001403348AB: mov         qword ptr [rsp+30h],r15
  00000001403348B0: je          00000001403349B2
  00000001403348B6: and         r8b,0Fh
  00000001403348BA: mov         qword ptr [rsp+68h],r12
  00000001403348BF: movzx       r12d,byte ptr [rsp+0000000000000080h]
  00000001403348C8: add         rcx,0CF0h
  00000001403348CF: movzx       ebx,r8b
  00000001403348D3: movzx       r15d,dl
  00000001403348D7: movzx       r8d,bx
  00000001403348DB: movzx       edx,r15w
  00000001403348DF: mov         qword ptr [rsp+70h],r13
  00000001403348E4: mov         byte ptr [rsp+20h],r12b
  00000001403348E9: call        0000000140411330
  00000001403348EE: mov         r9d,ebp
  00000001403348F1: mov         byte ptr [rsp+20h],r12b
  00000001403348F6: movzx       r8d,bx
  00000001403348FA: lea         rcx,[rsi+0000000000000F60h]
  0000000140334901: movzx       edx,r15w
  0000000140334905: call        0000000140411330
  000000014033490A: test        dil,dil
  000000014033490D: je          000000014033492D
  000000014033490F: movzx       edx,bx
  0000000140334912: lea         rcx,[rsi+0000000000000CF0h]
  0000000140334919: call        00000001404126A0
  000000014033491E: movzx       edx,bx
  0000000140334921: lea         rcx,[rsi+0000000000000F60h]
  0000000140334928: call        00000001404126A0
  000000014033492D: cmp         dword ptr [000000014070FD18h],0
  0000000140334934: mov         r13,qword ptr [rsp+70h]
  0000000140334939: jne         0000000140334996
  000000014033493B: mov         r9d,ebp
  000000014033493E: mov         byte ptr [rsp+20h],r12b
  0000000140334943: movzx       r8d,bx
  0000000140334947: lea         rcx,[rsi+0000000000000E28h]
  000000014033494E: movzx       edx,r15w
  0000000140334952: call        0000000140411330
  0000000140334957: mov         r9d,ebp
  000000014033495A: mov         byte ptr [rsp+20h],r12b
  000000014033495F: movzx       r8d,bx
  0000000140334963: lea         rcx,[rsi+0000000000001098h]
  000000014033496A: movzx       edx,r15w
  000000014033496E: call        0000000140411330
  0000000140334973: test        dil,dil
  0000000140334976: je          0000000140334996
  0000000140334978: movzx       edx,bx
  000000014033497B: lea         rcx,[rsi+0000000000000E28h]
  0000000140334982: call        00000001404126A0
  0000000140334987: movzx       edx,bx
  000000014033498A: lea         rcx,[rsi+0000000000001098h]
  0000000140334991: call        00000001404126A0
  0000000140334996: mov         r12,qword ptr [rsp+68h]
  000000014033499B: mov         r14,qword ptr [rsp+38h]
  00000001403349A0: mov         rbx,qword ptr [rsp+60h]
  00000001403349A5: mov         r15,qword ptr [rsp+30h]
  00000001403349AA: add         rsp,40h
  00000001403349AE: pop         rdi
  00000001403349AF: pop         rsi
  00000001403349B0: pop         rbp
  00000001403349B1: ret
  00000001403349B2: test        dil,dil
  00000001403349B5: jne         00000001403349FA
  00000001403349B7: add         rcx,0CF8h
  00000001403349BE: mov         edx,ebp
  00000001403349C0: call        0000000140412690
  00000001403349C5: lea         rcx,[rsi+0000000000000F68h]
  00000001403349CC: mov         edx,ebp
  00000001403349CE: call        0000000140412690
  00000001403349D3: cmp         dword ptr [000000014070FD18h],0
  00000001403349DA: jne         000000014033499B
  00000001403349DC: lea         rcx,[rsi+0000000000000E30h]
  00000001403349E3: mov         edx,ebp
  00000001403349E5: call        0000000140412690
  00000001403349EA: lea         rcx,[rsi+00000000000010A0h]
  00000001403349F1: mov         edx,ebp
  00000001403349F3: call        0000000140412690
  00000001403349F8: jmp         000000014033499B
  00000001403349FA: movzx       r15d,byte ptr [rsp+0000000000000080h]
  0000000140334A03: mov         r8d,ebp
  0000000140334A06: movzx       r14d,dil
  0000000140334A0A: movzx       r9d,r15b
  0000000140334A0E: movzx       edx,r14w
  0000000140334A12: add         rcx,0CF0h
  0000000140334A19: call        0000000140411420
  0000000140334A1E: movzx       r9d,r15b
  0000000140334A22: lea         rcx,[rsi+0000000000000F60h]
  0000000140334A29: mov         r8d,ebp
  0000000140334A2C: movzx       edx,r14w
  0000000140334A30: call        0000000140411420
  0000000140334A35: xor         edx,edx
  0000000140334A37: lea         rcx,[rsi+0000000000000CF0h]
  0000000140334A3E: call        00000001404126A0
  0000000140334A43: xor         edx,edx
  0000000140334A45: lea         rcx,[rsi+0000000000000F60h]
  0000000140334A4C: call        00000001404126A0
  0000000140334A51: cmp         dword ptr [000000014070FD18h],0
  0000000140334A58: jne         000000014033499B
  0000000140334A5E: movzx       r9d,r15b
  0000000140334A62: lea         rcx,[rsi+0000000000000E28h]
  0000000140334A69: mov         r8d,ebp
  0000000140334A6C: movzx       edx,r14w
  0000000140334A70: call        0000000140411420
  0000000140334A75: movzx       r9d,r15b
  0000000140334A79: lea         rcx,[rsi+0000000000001098h]
  0000000140334A80: mov         r8d,ebp
  0000000140334A83: movzx       edx,r14w
  0000000140334A87: call        0000000140411420
  0000000140334A8C: xor         edx,edx
  0000000140334A8E: lea         rcx,[rsi+0000000000000E28h]
  0000000140334A95: call        00000001404126A0
  0000000140334A9A: xor         edx,edx
  0000000140334A9C: lea         rcx,[rsi+0000000000001098h]
  0000000140334AA3: call        00000001404126A0
  0000000140334AA8: jmp         000000014033499B
  0000000140334AAD: int         3
  0000000140334AAE: int         3
  0000000140334AAF: int         3
  0000000140334AB0: test        r8b,0F0h
  0000000140334AB4: jne         0000000140334EF9
  0000000140334ABA: mov         byte ptr [rsp+10h],dl
  0000000140334ABE: push        rbx
  0000000140334ABF: push        rdi
  0000000140334AC0: push        r13
  0000000140334AC2: sub         rsp,40h
  0000000140334AC6: cmp         dword ptr [rcx+0000000000000D54h],0
  0000000140334ACD: mov         edi,r9d
  0000000140334AD0: movzx       eax,byte ptr [rcx+0000000000000D59h]
  0000000140334AD7: movzx       r13d,r8b
  0000000140334ADB: mov         qword ptr [rsp+60h],rbp
  0000000140334AE0: mov         rbx,rcx
  0000000140334AE3: mov         qword ptr [rsp+70h],rsi
  0000000140334AE8: mov         qword ptr [rsp+38h],r14
  0000000140334AED: mov         qword ptr [rsp+30h],r15
  0000000140334AF2: je          0000000140334CCF
  0000000140334AF8: xor         sil,sil
  0000000140334AFB: test        al,al
  0000000140334AFD: je          0000000140334C16
  0000000140334B03: movzx       eax,r8b
  0000000140334B07: mov         qword ptr [rsp+78h],r12
  0000000140334B0C: movzx       r12d,byte ptr [rsp+0000000000000080h]
  0000000140334B15: and         al,0Fh
  0000000140334B17: movzx       ebp,al
  0000000140334B1A: movzx       r15d,dl
  0000000140334B1E: xchg        ax,ax
  0000000140334B20: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334B27: mov         r9d,edi
  0000000140334B2A: movzx       eax,sil
  0000000140334B2E: movzx       r8d,bp
  0000000140334B32: imul        r14,rax,138h
  0000000140334B39: movzx       edx,r15w
  0000000140334B3D: mov         byte ptr [rsp+20h],r12b
  0000000140334B42: add         rcx,r14
  0000000140334B45: call        0000000140411330
  0000000140334B4A: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334B51: mov         r9d,edi
  0000000140334B54: add         rcx,r14
  0000000140334B57: mov         byte ptr [rsp+20h],r12b
  0000000140334B5C: movzx       r8d,bp
  0000000140334B60: movzx       edx,r15w
  0000000140334B64: call        0000000140411330
  0000000140334B69: mov         rax,qword ptr [rbx+0000000000000CF8h]
  0000000140334B70: mov         r9d,edi
  0000000140334B73: movzx       r8d,bp
  0000000140334B77: mov         byte ptr [rsp+20h],r12b
  0000000140334B7C: movzx       edx,r15w
  0000000140334B80: lea         rcx,[r14+rax]
  0000000140334B84: call        0000000140411330
  0000000140334B89: cmp         dword ptr [rbx+0000000000000D60h],0
  0000000140334B90: je          0000000140334BF9
  0000000140334B92: cmp         dword ptr [000000014070FD18h],0
  0000000140334B99: jne         0000000140334BF9
  0000000140334B9B: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140334BA2: mov         r9d,edi
  0000000140334BA5: add         rcx,r14
  0000000140334BA8: mov         byte ptr [rsp+20h],r12b
  0000000140334BAD: movzx       r8d,bp
  0000000140334BB1: movzx       edx,r15w
  0000000140334BB5: call        0000000140411330
  0000000140334BBA: mov         rcx,qword ptr [rbx+0000000000000D10h]
  0000000140334BC1: mov         r9d,edi
  0000000140334BC4: add         rcx,r14
  0000000140334BC7: mov         byte ptr [rsp+20h],r12b
  0000000140334BCC: movzx       r8d,bp
  0000000140334BD0: movzx       edx,r15w
  0000000140334BD4: call        0000000140411330
  0000000140334BD9: mov         rax,qword ptr [rbx+0000000000000D18h]
  0000000140334BE0: mov         r9d,edi
  0000000140334BE3: movzx       r8d,bp
  0000000140334BE7: mov         byte ptr [rsp+20h],r12b
  0000000140334BEC: movzx       edx,r15w
  0000000140334BF0: lea         rcx,[r14+rax]
  0000000140334BF4: call        0000000140411330
  0000000140334BF9: movzx       eax,byte ptr [rbx+0000000000000D59h]
  0000000140334C00: inc         sil
  0000000140334C03: cmp         sil,al
  0000000140334C06: jb          0000000140334B20
  0000000140334C0C: movzx       edx,byte ptr [rsp+68h]
  0000000140334C11: mov         r12,qword ptr [rsp+78h]
  0000000140334C16: test        dl,dl
  0000000140334C18: je          0000000140334EDD
  0000000140334C1E: xor         bpl,bpl
  0000000140334C21: test        al,al
  0000000140334C23: je          0000000140334EDD
  0000000140334C29: and         r13b,0Fh
  0000000140334C2D: movzx       esi,r13b
  0000000140334C31: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334C38: movzx       edx,si
  0000000140334C3B: movzx       eax,bpl
  0000000140334C3F: imul        rdi,rax,138h
  0000000140334C46: add         rcx,rdi
  0000000140334C49: call        00000001404126A0
  0000000140334C4E: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334C55: movzx       edx,si
  0000000140334C58: add         rcx,rdi
  0000000140334C5B: call        00000001404126A0
  0000000140334C60: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  0000000140334C67: movzx       edx,si
  0000000140334C6A: add         rcx,rdi
  0000000140334C6D: call        00000001404126A0
  0000000140334C72: cmp         dword ptr [rbx+0000000000000D60h],0
  0000000140334C79: je          0000000140334CBA
  0000000140334C7B: cmp         dword ptr [000000014070FD18h],0
  0000000140334C82: jne         0000000140334CBA
  0000000140334C84: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140334C8B: movzx       edx,si
  0000000140334C8E: add         rcx,rdi
  0000000140334C91: call        00000001404126A0
  0000000140334C96: mov         rcx,qword ptr [rbx+0000000000000D10h]
  0000000140334C9D: movzx       edx,si
  0000000140334CA0: add         rcx,rdi
  0000000140334CA3: call        00000001404126A0
  0000000140334CA8: mov         rcx,qword ptr [rbx+0000000000000D18h]
  0000000140334CAF: movzx       edx,si
  0000000140334CB2: add         rcx,rdi
  0000000140334CB5: call        00000001404126A0
  0000000140334CBA: inc         bpl
  0000000140334CBD: cmp         bpl,byte ptr [rbx+0000000000000D59h]
  0000000140334CC4: jb          0000000140334C31
  0000000140334CCA: jmp         0000000140334EDD
  0000000140334CCF: test        dl,dl
  0000000140334CD1: jne         0000000140334D92
  0000000140334CD7: xor         bpl,bpl
  0000000140334CDA: test        al,al
  0000000140334CDC: je          0000000140334EDD
  0000000140334CE2: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334CE9: mov         edx,edi
  0000000140334CEB: movzx       eax,bpl
  0000000140334CEF: add         rcx,8
  0000000140334CF3: imul        rsi,rax,138h
  0000000140334CFA: add         rcx,rsi
  0000000140334CFD: call        0000000140412690
  0000000140334D02: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334D09: mov         edx,edi
  0000000140334D0B: add         rcx,8
  0000000140334D0F: add         rcx,rsi
  0000000140334D12: call        0000000140412690
  0000000140334D17: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  0000000140334D1E: mov         edx,edi
  0000000140334D20: add         rcx,8
  0000000140334D24: add         rcx,rsi
  0000000140334D27: call        0000000140412690
  0000000140334D2C: cmp         dword ptr [rbx+0000000000000D60h],0
  0000000140334D33: je          0000000140334D7D
  0000000140334D35: cmp         dword ptr [000000014070FD18h],0
  0000000140334D3C: jne         0000000140334D7D
  0000000140334D3E: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140334D45: mov         edx,edi
  0000000140334D47: add         rcx,8
  0000000140334D4B: add         rcx,rsi
  0000000140334D4E: call        0000000140412690
  0000000140334D53: mov         rcx,qword ptr [rbx+0000000000000D10h]
  0000000140334D5A: mov         edx,edi
  0000000140334D5C: add         rcx,8
  0000000140334D60: add         rcx,rsi
  0000000140334D63: call        0000000140412690
  0000000140334D68: mov         rcx,qword ptr [rbx+0000000000000D18h]
  0000000140334D6F: mov         edx,edi
  0000000140334D71: add         rcx,8
  0000000140334D75: add         rcx,rsi
  0000000140334D78: call        0000000140412690
  0000000140334D7D: inc         bpl
  0000000140334D80: cmp         bpl,byte ptr [rbx+0000000000000D59h]
  0000000140334D87: jb          0000000140334CE2
  0000000140334D8D: jmp         0000000140334EDD
  0000000140334D92: xor         sil,sil
  0000000140334D95: test        al,al
  0000000140334D97: je          0000000140334EDD
  0000000140334D9D: movzx       r15d,byte ptr [rsp+0000000000000080h]
  0000000140334DA6: movzx       ebp,dl
  0000000140334DA9: nop         dword ptr [rax+0000000000000000h]
  0000000140334DB0: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334DB7: movzx       r9d,r15b
  0000000140334DBB: movzx       eax,sil
  0000000140334DBF: mov         r8d,edi
  0000000140334DC2: imul        r14,rax,138h
  0000000140334DC9: movzx       edx,bp
  0000000140334DCC: add         rcx,r14
  0000000140334DCF: call        0000000140411420
  0000000140334DD4: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334DDB: movzx       r9d,r15b
  0000000140334DDF: add         rcx,r14
  0000000140334DE2: mov         r8d,edi
  0000000140334DE5: movzx       edx,bp
  0000000140334DE8: call        0000000140411420
  0000000140334DED: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  0000000140334DF4: movzx       r9d,r15b
  0000000140334DF8: add         rcx,r14
  0000000140334DFB: mov         r8d,edi
  0000000140334DFE: movzx       edx,bp
  0000000140334E01: call        0000000140411420
  0000000140334E06: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140334E0D: xor         edx,edx
  0000000140334E0F: add         rcx,r14
  0000000140334E12: call        00000001404126A0
  0000000140334E17: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140334E1E: xor         edx,edx
  0000000140334E20: add         rcx,r14
  0000000140334E23: call        00000001404126A0
  0000000140334E28: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  0000000140334E2F: xor         edx,edx
  0000000140334E31: add         rcx,r14
  0000000140334E34: call        00000001404126A0
  0000000140334E39: cmp         dword ptr [rbx+0000000000000D60h],0
  0000000140334E40: je          0000000140334ECD
  0000000140334E46: cmp         dword ptr [000000014070FD18h],0
  0000000140334E4D: jne         0000000140334ECD
  0000000140334E4F: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140334E56: movzx       r9d,r15b
  0000000140334E5A: add         rcx,r14
  0000000140334E5D: mov         r8d,edi
  0000000140334E60: movzx       edx,bp
  0000000140334E63: call        0000000140411420
  0000000140334E68: mov         rcx,qword ptr [rbx+0000000000000D10h]
  0000000140334E6F: movzx       r9d,r15b
  0000000140334E73: add         rcx,r14
  0000000140334E76: mov         r8d,edi
  0000000140334E79: movzx       edx,bp
  0000000140334E7C: call        0000000140411420
  0000000140334E81: mov         rcx,qword ptr [rbx+0000000000000D18h]
  0000000140334E88: movzx       r9d,r15b
  0000000140334E8C: add         rcx,r14
  0000000140334E8F: mov         r8d,edi
  0000000140334E92: movzx       edx,bp
  0000000140334E95: call        0000000140411420
  0000000140334E9A: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140334EA1: xor         edx,edx
  0000000140334EA3: add         rcx,r14
  0000000140334EA6: call        00000001404126A0
  0000000140334EAB: mov         rcx,qword ptr [rbx+0000000000000D10h]
  0000000140334EB2: xor         edx,edx
  0000000140334EB4: add         rcx,r14
  0000000140334EB7: call        00000001404126A0
  0000000140334EBC: mov         rcx,qword ptr [rbx+0000000000000D18h]
  0000000140334EC3: xor         edx,edx
  0000000140334EC5: add         rcx,r14
  0000000140334EC8: call        00000001404126A0
  0000000140334ECD: inc         sil
  0000000140334ED0: cmp         sil,byte ptr [rbx+0000000000000D59h]
  0000000140334ED7: jb          0000000140334DB0
  0000000140334EDD: mov         r14,qword ptr [rsp+38h]
  0000000140334EE2: mov         rsi,qword ptr [rsp+70h]
  0000000140334EE7: mov         rbp,qword ptr [rsp+60h]
  0000000140334EEC: mov         r15,qword ptr [rsp+30h]
  0000000140334EF1: add         rsp,40h
  0000000140334EF5: pop         r13
  0000000140334EF7: pop         rdi
  0000000140334EF8: pop         rbx
  0000000140334EF9: ret
  0000000140334EFA: int         3
  0000000140334EFB: int         3
  0000000140334EFC: int         3
  0000000140334EFD: int         3
  0000000140334EFE: int         3
  0000000140334EFF: int         3
  0000000140334F00: mov         qword ptr [rsp+8],rbx
  0000000140334F05: mov         qword ptr [rsp+10h],rbp
  0000000140334F0A: mov         qword ptr [rsp+18h],rsi
  0000000140334F0F: mov         qword ptr [rsp+20h],rdi
  0000000140334F14: push        r14
  0000000140334F16: sub         rsp,30h
  0000000140334F1A: cmp         dword ptr [rcx+0000000000000F94h],0
  0000000140334F21: movzx       r14d,r9b
  0000000140334F25: mov         esi,r8d
  0000000140334F28: movzx       ebp,dl
  0000000140334F2B: mov         rdi,rcx
  0000000140334F2E: je          0000000140334F65
  0000000140334F30: xor         bl,bl
  0000000140334F32: nop         dword ptr [rax]
  0000000140334F36: nop         word ptr [rax+rax+0000000000000000h]
  0000000140334F40: mov         rax,qword ptr [rdi]
  0000000140334F43: mov         r9d,esi
  0000000140334F46: movzx       r8d,bl
  0000000140334F4A: mov         byte ptr [rsp+20h],r14b
  0000000140334F4F: movzx       edx,bpl
  0000000140334F53: mov         rcx,rdi
  0000000140334F56: call        qword ptr [rax+0000000000000148h]
  0000000140334F5C: inc         bl
  0000000140334F5E: cmp         bl,7
  0000000140334F61: jb          0000000140334F40
  0000000140334F63: jmp         0000000140334FE3
  0000000140334F65: test        bpl,bpl
  0000000140334F68: jne         0000000140334F91
  0000000140334F6A: add         rcx,0CF8h
  0000000140334F71: mov         edx,esi
  0000000140334F73: call        0000000140412690
  0000000140334F78: cmp         dword ptr [000000014070FD18h],0
  0000000140334F7F: jne         0000000140334FE3
  0000000140334F81: lea         rcx,[rdi+0000000000000E30h]
  0000000140334F88: mov         edx,esi
  0000000140334F8A: call        0000000140412690
  0000000140334F8F: jmp         0000000140334FE3
  0000000140334F91: movzx       ebp,bpl
  0000000140334F95: movzx       r9d,r14b
  0000000140334F99: movzx       edx,bp
  0000000140334F9C: add         rcx,0CF0h
  0000000140334FA3: call        0000000140411420
  0000000140334FA8: xor         edx,edx
  0000000140334FAA: lea         rcx,[rdi+0000000000000CF0h]
  0000000140334FB1: call        00000001404126A0
  0000000140334FB6: cmp         dword ptr [000000014070FD18h],0
  0000000140334FBD: jne         0000000140334FE3
  0000000140334FBF: movzx       r9d,r14b
  0000000140334FC3: lea         rcx,[rdi+0000000000000E28h]
  0000000140334FCA: mov         r8d,esi
  0000000140334FCD: movzx       edx,bp
  0000000140334FD0: call        0000000140411420
  0000000140334FD5: xor         edx,edx
  0000000140334FD7: lea         rcx,[rdi+0000000000000E28h]
  0000000140334FDE: call        00000001404126A0
  0000000140334FE3: mov         rbx,qword ptr [rsp+40h]
  0000000140334FE8: mov         rbp,qword ptr [rsp+48h]
  0000000140334FED: mov         rsi,qword ptr [rsp+50h]
  0000000140334FF2: mov         rdi,qword ptr [rsp+58h]
  0000000140334FF7: add         rsp,30h
  0000000140334FFB: pop         r14
  0000000140334FFD: ret
  0000000140334FFE: int         3
  0000000140334FFF: int         3
  0000000140335000: mov         qword ptr [rsp+8],rbx
  0000000140335005: mov         qword ptr [rsp+10h],rbp
  000000014033500A: mov         qword ptr [rsp+18h],rsi
  000000014033500F: mov         qword ptr [rsp+20h],rdi
  0000000140335014: push        r14
  0000000140335016: sub         rsp,30h
  000000014033501A: cmp         dword ptr [rcx+0000000000000F8Ch],0
  0000000140335021: movzx       r14d,r9b
  0000000140335025: mov         esi,r8d
  0000000140335028: movzx       ebp,dl
  000000014033502B: mov         rdi,rcx
  000000014033502E: je          0000000140335065
  0000000140335030: xor         bl,bl
  0000000140335032: nop         dword ptr [rax]
  0000000140335036: nop         word ptr [rax+rax+0000000000000000h]
  0000000140335040: mov         rax,qword ptr [rdi]
  0000000140335043: mov         r9d,esi
  0000000140335046: movzx       r8d,bl
  000000014033504A: mov         byte ptr [rsp+20h],r14b
  000000014033504F: movzx       edx,bpl
  0000000140335053: mov         rcx,rdi
  0000000140335056: call        qword ptr [rax+0000000000000148h]
  000000014033505C: inc         bl
  000000014033505E: cmp         bl,7
  0000000140335061: jb          0000000140335040
  0000000140335063: jmp         00000001403350E3
  0000000140335065: test        bpl,bpl
  0000000140335068: jne         0000000140335091
  000000014033506A: add         rcx,0CF0h
  0000000140335071: mov         edx,esi
  0000000140335073: call        0000000140412690
  0000000140335078: cmp         dword ptr [000000014070FD18h],0
  000000014033507F: jne         00000001403350E3
  0000000140335081: lea         rcx,[rdi+0000000000000E28h]
  0000000140335088: mov         edx,esi
  000000014033508A: call        0000000140412690
  000000014033508F: jmp         00000001403350E3
  0000000140335091: movzx       ebp,bpl
  0000000140335095: movzx       r9d,r14b
  0000000140335099: movzx       edx,bp
  000000014033509C: add         rcx,0CE8h
  00000001403350A3: call        0000000140411420
  00000001403350A8: xor         edx,edx
  00000001403350AA: lea         rcx,[rdi+0000000000000CE8h]
  00000001403350B1: call        00000001404126A0
  00000001403350B6: cmp         dword ptr [000000014070FD18h],0
  00000001403350BD: jne         00000001403350E3
  00000001403350BF: movzx       r9d,r14b
  00000001403350C3: lea         rcx,[rdi+0000000000000E20h]
  00000001403350CA: mov         r8d,esi
  00000001403350CD: movzx       edx,bp
  00000001403350D0: call        0000000140411420
  00000001403350D5: xor         edx,edx
  00000001403350D7: lea         rcx,[rdi+0000000000000E20h]
  00000001403350DE: call        00000001404126A0
  00000001403350E3: mov         rbx,qword ptr [rsp+40h]
  00000001403350E8: mov         rbp,qword ptr [rsp+48h]
  00000001403350ED: mov         rsi,qword ptr [rsp+50h]
  00000001403350F2: mov         rdi,qword ptr [rsp+58h]
  00000001403350F7: add         rsp,30h
  00000001403350FB: pop         r14
  00000001403350FD: ret
  00000001403350FE: int         3
  00000001403350FF: int         3
  0000000140335100: mov         byte ptr [rsp+20h],r9b
  0000000140335105: mov         byte ptr [rsp+10h],dl
  0000000140335109: push        rbx
  000000014033510A: push        rbp
  000000014033510B: push        rsi
  000000014033510C: push        rdi
  000000014033510D: push        r13
  000000014033510F: sub         rsp,40h
  0000000140335113: cmp         dword ptr [rcx+0000000000002420h],0
  000000014033511A: movzx       ebp,r9b
  000000014033511E: mov         r13d,r8d
  0000000140335121: movzx       edi,dl
  0000000140335124: mov         rbx,rcx
  0000000140335127: je          000000014033515A
  0000000140335129: xor         sil,sil
  000000014033512C: nop         dword ptr [rax]
  0000000140335130: mov         rax,qword ptr [rbx]
  0000000140335133: mov         r9d,r13d
  0000000140335136: movzx       r8d,sil
  000000014033513A: mov         byte ptr [rsp+20h],bpl
  000000014033513F: movzx       edx,dil
  0000000140335143: mov         rcx,rbx
  0000000140335146: call        qword ptr [rax+0000000000000148h]
  000000014033514C: inc         sil
  000000014033514F: cmp         sil,7
  0000000140335153: jb          0000000140335130
  0000000140335155: jmp         00000001403352A0
  000000014033515A: test        dil,dil
  000000014033515D: jne         00000001403351AF
  000000014033515F: add         rcx,0D18h
  0000000140335166: mov         edx,r13d
  0000000140335169: call        0000000140412690
  000000014033516E: lea         rcx,[rbx+0000000000000E50h]
  0000000140335175: mov         edx,r13d
  0000000140335178: call        0000000140412690
  000000014033517D: lea         rcx,[rbx+0000000000000F88h]
  0000000140335184: mov         edx,r13d
  0000000140335187: call        0000000140412690
  000000014033518C: lea         rcx,[rbx+00000000000010C0h]
  0000000140335193: mov         edx,r13d
  0000000140335196: call        0000000140412690
  000000014033519B: lea         rcx,[rbx+00000000000011F8h]
  00000001403351A2: mov         edx,r13d
  00000001403351A5: call        0000000140412690
  00000001403351AA: jmp         00000001403352A0
  00000001403351AF: mov         qword ptr [rsp+70h],r12
  00000001403351B4: movzx       r9d,bpl
  00000001403351B8: mov         qword ptr [rsp+38h],r14
  00000001403351BD: add         rcx,0D10h
  00000001403351C4: movzx       r14d,dil
  00000001403351C8: movzx       edx,r14w
  00000001403351CC: mov         qword ptr [rsp+30h],r15
  00000001403351D1: call        0000000140411420
  00000001403351D6: movzx       r9d,bpl
  00000001403351DA: lea         rcx,[rbx+0000000000000E48h]
  00000001403351E1: mov         r8d,r13d
  00000001403351E4: movzx       edx,r14w
  00000001403351E8: call        0000000140411420
  00000001403351ED: movzx       r9d,byte ptr [rsp+0000000000000088h]
  00000001403351F6: lea         rbp,[rbx+0000000000000F80h]
  00000001403351FD: mov         rcx,rbp
  0000000140335200: mov         r8d,r13d
  0000000140335203: movzx       edx,r14w
  0000000140335207: call        0000000140411420
  000000014033520C: movzx       r9d,byte ptr [rsp+0000000000000088h]
  0000000140335215: lea         rsi,[rbx+00000000000010B8h]
  000000014033521C: mov         rcx,rsi
  000000014033521F: mov         r8d,r13d
  0000000140335222: movzx       edx,r14w
  0000000140335226: call        0000000140411420
  000000014033522B: movzx       r9d,byte ptr [rsp+0000000000000088h]
  0000000140335234: lea         rdi,[rbx+00000000000011F0h]
  000000014033523B: mov         rcx,rdi
  000000014033523E: mov         r8d,r13d
  0000000140335241: movzx       edx,r14w
  0000000140335245: call        0000000140411420
  000000014033524A: xor         edx,edx
  000000014033524C: lea         rcx,[rbx+0000000000000D10h]
  0000000140335253: call        00000001404126A0
  0000000140335258: xor         edx,edx
  000000014033525A: lea         rcx,[rbx+0000000000000E48h]
  0000000140335261: call        00000001404126A0
  0000000140335266: xor         edx,edx
  0000000140335268: mov         rcx,rbp
  000000014033526B: call        00000001404126A0
  0000000140335270: xor         edx,edx
  0000000140335272: mov         rcx,rsi
  0000000140335275: call        00000001404126A0
  000000014033527A: xor         edx,edx
  000000014033527C: mov         rcx,rdi
  000000014033527F: call        00000001404126A0
  0000000140335284: movzx       edi,byte ptr [rsp+78h]
  0000000140335289: movzx       ebp,byte ptr [rsp+0000000000000088h]
  0000000140335291: mov         r15,qword ptr [rsp+30h]
  0000000140335296: mov         r14,qword ptr [rsp+38h]
  000000014033529B: mov         r12,qword ptr [rsp+70h]
  00000001403352A0: cmp         qword ptr [rbx+0000000000001360h],0
  00000001403352A8: je          00000001403352D9
  00000001403352AA: xor         sil,sil
  00000001403352AD: nop         dword ptr [rax]
  00000001403352B0: mov         rax,qword ptr [rbx]
  00000001403352B3: movzx       r8d,sil
  00000001403352B7: or          r8b,10h
  00000001403352BB: mov         byte ptr [rsp+20h],bpl
  00000001403352C0: mov         r9d,r13d
  00000001403352C3: movzx       edx,dil
  00000001403352C7: mov         rcx,rbx
  00000001403352CA: call        qword ptr [rax+0000000000000148h]
  00000001403352D0: inc         sil
  00000001403352D3: cmp         sil,7
  00000001403352D7: jb          00000001403352B0
  00000001403352D9: cmp         qword ptr [rbx+0000000000001888h],0
  00000001403352E1: je          0000000140335319
  00000001403352E3: xor         sil,sil
  00000001403352E6: nop         word ptr [rax+rax+0000000000000000h]
  00000001403352F0: mov         rax,qword ptr [rbx]
  00000001403352F3: movzx       r8d,sil
  00000001403352F7: or          r8b,20h
  00000001403352FB: mov         byte ptr [rsp+20h],bpl
  0000000140335300: mov         r9d,r13d
  0000000140335303: movzx       edx,dil
  0000000140335307: mov         rcx,rbx
  000000014033530A: call        qword ptr [rax+0000000000000148h]
  0000000140335310: inc         sil
  0000000140335313: cmp         sil,7
  0000000140335317: jb          00000001403352F0
  0000000140335319: cmp         dword ptr [rbx+0000000000002418h],0
  0000000140335320: je          0000000140335359
  0000000140335322: cmp         qword ptr [rbx+0000000000001DB0h],0
  000000014033532A: je          0000000140335359
  000000014033532C: xor         sil,sil
  000000014033532F: nop
  0000000140335330: mov         rax,qword ptr [rbx]
  0000000140335333: movzx       r8d,sil
  0000000140335337: or          r8b,30h
  000000014033533B: mov         byte ptr [rsp+20h],bpl
  0000000140335340: mov         r9d,r13d
  0000000140335343: movzx       edx,dil
  0000000140335347: mov         rcx,rbx
  000000014033534A: call        qword ptr [rax+0000000000000148h]
  0000000140335350: inc         sil
  0000000140335353: cmp         sil,7
  0000000140335357: jb          0000000140335330
  0000000140335359: add         rsp,40h
  000000014033535D: pop         r13
  000000014033535F: pop         rdi
  0000000140335360: pop         rsi
  0000000140335361: pop         rbp
  0000000140335362: pop         rbx
  0000000140335363: ret
  0000000140335364: int         3
  0000000140335365: int         3
  0000000140335366: int         3
  0000000140335367: int         3
  0000000140335368: int         3
  0000000140335369: int         3
  000000014033536A: int         3
  000000014033536B: int         3
  000000014033536C: int         3
  000000014033536D: int         3
  000000014033536E: int         3
  000000014033536F: int         3
  0000000140335370: mov         byte ptr [rsp+20h],r9b
  0000000140335375: mov         byte ptr [rsp+10h],dl
  0000000140335379: push        rbx
  000000014033537A: push        rbp
  000000014033537B: push        rsi
  000000014033537C: push        rdi
  000000014033537D: push        r13
  000000014033537F: sub         rsp,40h
  0000000140335383: cmp         dword ptr [rcx+00000000000052A0h],0
  000000014033538A: movzx       edi,r9b
  000000014033538E: mov         r13d,r8d
  0000000140335391: movzx       esi,dl
  0000000140335394: mov         rbx,rcx
  0000000140335397: je          00000001403353CA
  0000000140335399: xor         bpl,bpl
  000000014033539C: nop         dword ptr [rax]
  00000001403353A0: mov         rax,qword ptr [rbx]
  00000001403353A3: mov         r9d,r13d
  00000001403353A6: movzx       r8d,bpl
  00000001403353AA: mov         byte ptr [rsp+20h],dil
  00000001403353AF: movzx       edx,sil
  00000001403353B3: mov         rcx,rbx
  00000001403353B6: call        qword ptr [rax+0000000000000148h]
  00000001403353BC: inc         bpl
  00000001403353BF: cmp         bpl,7
  00000001403353C3: jb          00000001403353A0
  00000001403353C5: jmp         00000001403356A6
  00000001403353CA: test        sil,sil
  00000001403353CD: jne         0000000140335499
  00000001403353D3: add         rcx,0D18h
  00000001403353DA: mov         edx,r13d
  00000001403353DD: call        0000000140412690
  00000001403353E2: lea         rcx,[rbx+0000000000000F88h]
  00000001403353E9: mov         edx,r13d
  00000001403353EC: call        0000000140412690
  00000001403353F1: lea         rcx,[rbx+00000000000011F8h]
  00000001403353F8: mov         edx,r13d
  00000001403353FB: call        0000000140412690
  0000000140335400: lea         rcx,[rbx+0000000000001468h]
  0000000140335407: mov         edx,r13d
  000000014033540A: call        0000000140412690
  000000014033540F: lea         rcx,[rbx+00000000000016D8h]
  0000000140335416: mov         edx,r13d
  0000000140335419: call        0000000140412690
  000000014033541E: lea         rcx,[rbx+0000000000001948h]
  0000000140335425: mov         edx,r13d
  0000000140335428: call        0000000140412690
  000000014033542D: cmp         dword ptr [000000014070FD18h],0
  0000000140335434: jne         00000001403356A6
  000000014033543A: lea         rcx,[rbx+0000000000000E50h]
  0000000140335441: mov         edx,r13d
  0000000140335444: call        0000000140412690
  0000000140335449: lea         rcx,[rbx+00000000000010C0h]
  0000000140335450: 41

  Summary

      589000 .text
