Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  0000000140314350: mov         qword ptr [rsp+20h],rbx
  0000000140314355: push        rbp
  0000000140314356: push        rsi
  0000000140314357: push        rdi
  0000000140314358: push        r12
  000000014031435A: push        r13
  000000014031435C: push        r14
  000000014031435E: push        r15
  0000000140314360: lea         rbp,[rsp-27h]
  0000000140314365: sub         rsp,100h
  000000014031436C: mov         rax,qword ptr [00000001406649D8h]
  0000000140314373: xor         rax,rsp
  0000000140314376: mov         qword ptr [rbp+1Fh],rax
  000000014031437A: mov         word ptr [rsp+28h],r9w
  0000000140314380: mov         rbx,rcx
  0000000140314383: mov         qword ptr [rbp-61h],r8
  0000000140314387: movzx       esi,dx
  000000014031438A: call        00000001403074D0
  000000014031438F: lea         rax,[00000001405AA460h]
  0000000140314396: mov         qword ptr [rbx],rax
  0000000140314399: lea         r13,[rbx+0000000000000CD0h]
  00000001403143A0: mov         rax,qword ptr [000000014065CB10h]
  00000001403143A7: lea         r12,[rbx+0000000000000D20h]
  00000001403143AE: mov         qword ptr [r13],rax
  00000001403143B2: mov         rcx,r12
  00000001403143B5: movzx       edx,word ptr [00000001405C067Ch]
  00000001403143BC: call        0000000140421010
  00000001403143C1: mov         rax,qword ptr [000000014065CB10h]
  00000001403143C8: lea         rcx,[00000001405AB1F8h]
  00000001403143CF: mov         word ptr [rbx+8],si
  00000001403143D3: mov         r14d,1
  00000001403143D9: mov         dword ptr [rbx+0000000000000D54h],r14d
  00000001403143E0: xor         r15d,r15d
  00000001403143E3: mov         byte ptr [rbx+0000000000000D59h],r14b
  00000001403143EA: mov         edx,esi
  00000001403143EC: mov         dword ptr [rbx+0000000000000D5Ch],r15d
  00000001403143F3: mov         edi,esi
  00000001403143F5: mov         qword ptr [rbx+0000000000000D60h],r14
  00000001403143FC: mov         dword ptr [rbx+30h],0A0000h
  0000000140314403: mov         dword ptr [rbx+34h],0AFFF6h
  000000014031440A: mov         dword ptr [rbx+38h],0FFF6h
  0000000140314411: mov         dword ptr [rbx+3Ch],0FFF6FFF6h
  0000000140314418: mov         dword ptr [rbx+40h],0FFF60000h
  000000014031441F: mov         dword ptr [rbx+44h],0FFF6000Ah
  0000000140314426: mov         dword ptr [rbx+48h],0Ah
  000000014031442D: mov         dword ptr [rbx+4Ch],0A000Ah
  0000000140314434: mov         qword ptr [rsp+20h],rax
  0000000140314439: movzx       eax,byte ptr [00000001405ACEABh]
  0000000140314440: mov         byte ptr [rbx+0000000000000D58h],al
  0000000140314446: call        0000000140400170
  000000014031444B: mov         rdx,rax
  000000014031444E: lea         rcx,[rbp-41h]
  0000000140314452: call        00000001403FF7C0
  0000000140314457: mov         rcx,rbx
  000000014031445A: mov         rdx,qword ptr [rax]
  000000014031445D: call        0000000140341010
  0000000140314462: test        al,al
  0000000140314464: jne         0000000140314561
  000000014031446A: and         edi,0F00h
  0000000140314470: je          0000000140314513
  0000000140314476: cmp         edi,100h
  000000014031447C: je          0000000140314503
  0000000140314482: cmp         edi,200h
  0000000140314488: jne         0000000140314561
  000000014031448E: lea         rax,[00000001405AB538h]
  0000000140314495: mov         byte ptr [rbx+22h],0FFh
  0000000140314499: lea         rdx,[00000001405FFF3Ch]
  00000001403144A0: mov         qword ptr [rbx+28h],rax
  00000001403144A4: lea         rcx,[rsp+20h]
  00000001403144A9: mov         dword ptr [rbx+0000000000000D54h],r15d
  00000001403144B0: mov         dword ptr [rbx+0000000000000D5Ch],r14d
  00000001403144B7: mov         byte ptr [rbx+0000000000000D59h],6
  00000001403144BE: mov         dword ptr [rbx+24h],8
  00000001403144C5: call        00000001403FD810
  00000001403144CA: lea         rdx,[00000001405ABE48h]
  00000001403144D1: mov         word ptr [rbx+0Ah],0E0Eh
  00000001403144D7: mov         rcx,r13
  00000001403144DA: mov         dword ptr [rbx+0000000000000D60h],r15d
  00000001403144E1: mov         byte ptr [rbx+00000000000005F0h],7
  00000001403144E8: call        00000001403FD810
  00000001403144ED: movzx       eax,byte ptr [00000001405ACE93h]
  00000001403144F4: mov         byte ptr [rbx+0000000000000D58h],al
  00000001403144FA: mov         dword ptr [rbx+0000000000000D64h],r14d
  0000000140314501: jmp         0000000140314561
  0000000140314503: mov         dword ptr [rbx+0000000000000D5Ch],r14d
  000000014031450A: lea         rdx,[00000001405ABE40h]
  0000000140314511: jmp         0000000140314528
  0000000140314513: mov         dword ptr [rbx+0000000000000D60h],r15d
  000000014031451A: lea         rdx,[00000001405ABE10h]
  0000000140314521: mov         dword ptr [rbx+0000000000000D64h],r14d
  0000000140314528: mov         rcx,r13
  000000014031452B: mov         byte ptr [rbx+22h],0FFh
  000000014031452F: mov         word ptr [rbx+0Ah],808h
  0000000140314535: mov         dword ptr [rbx+0000000000000D54h],r15d
  000000014031453C: mov         byte ptr [rbx+0000000000000D59h],4
  0000000140314543: mov         dword ptr [rbx+24h],8
  000000014031454A: mov         byte ptr [rbx+00000000000005F0h],5
  0000000140314551: call        00000001403FD810
  0000000140314556: lea         rax,[00000001405AB538h]
  000000014031455D: mov         qword ptr [rbx+28h],rax
  0000000140314561: mov         rax,qword ptr [0000000140667548h]
  0000000140314568: movzx       edx,si
  000000014031456B: movzx       r8d,byte ptr [rbx+0Ah]
  0000000140314570: mov         rcx,qword ptr [rax+0000000000001090h]
  0000000140314577: call        000000014023AE30
  000000014031457C: lea         rdx,[00000001405EB7ADh]
  0000000140314583: mov         byte ptr [rbx+0Bh],al
  0000000140314586: lea         rcx,[rbx+00000000000005F7h]
  000000014031458D: mov         byte ptr [rbx+0Ah],al
  0000000140314590: call        00000001403FFA80
  0000000140314595: test        eax,eax
  0000000140314597: je          00000001403145AC
  0000000140314599: mov         r8,r13
  000000014031459C: lea         rdx,[rbp-41h]
  00000001403145A0: lea         rcx,[rbx+00000000000005F7h]
  00000001403145A7: call        00000001403FF890
  00000001403145AC: mov         rcx,rbx
  00000001403145AF: call        0000000140316900
  00000001403145B4: movzx       eax,byte ptr [rbx+0000000000000D59h]
  00000001403145BB: mov         rcx,0FFFFFFFFFFFFFFFFh
  00000001403145C2: lea         rdi,[rax+rax*2]
  00000001403145C6: mov         eax,138h
  00000001403145CB: mul         rax,rdi
  00000001403145CE: cmovo       rax,rcx
  00000001403145D2: add         rax,8
  00000001403145D6: cmovb       rax,rcx
  00000001403145DA: mov         rcx,rax
  00000001403145DD: call        00000001404F77C4
  00000001403145E2: test        rax,rax
  00000001403145E5: je          000000014031460D
  00000001403145E7: mov         qword ptr [rax],rdi
  00000001403145EA: lea         r14,[rax+8]
  00000001403145EE: mov         rsi,r14
  00000001403145F1: test        rdi,rdi
  00000001403145F4: je          0000000140314610
  00000001403145F6: mov         rcx,rsi
  00000001403145F9: call        0000000140410F70
  00000001403145FE: add         rsi,138h
  0000000140314605: sub         rdi,1
  0000000140314609: jne         00000001403145F6
  000000014031460B: jmp         0000000140314610
  000000014031460D: mov         r14,r15
  0000000140314610: movzx       ecx,byte ptr [rbx+0000000000000D59h]
  0000000140314617: imul        rax,rcx,138h
  000000014031461E: mov         qword ptr [rbx+0000000000000CE8h],r14
  0000000140314625: add         rax,r14
  0000000140314628: mov         qword ptr [rbx+0000000000000CF0h],rax
  000000014031462F: imul        rax,rcx,270h
  0000000140314636: add         rax,r14
  0000000140314639: mov         qword ptr [rbx+0000000000000CF8h],rax
  0000000140314640: test        cl,cl
  0000000140314642: je          00000001403149CF
  0000000140314648: mov         r14b,31h
  000000014031464B: nop         dword ptr [rax+rax]
  0000000140314650: lea         r8,[00000001405AB498h]
  0000000140314657: mov         rdx,r13
  000000014031465A: lea         rcx,[rsp+40h]
  000000014031465F: call        00000001403FD8E0
  0000000140314664: mov         rdx,rax
  0000000140314667: lea         r8,[rsp+20h]
  000000014031466C: lea         rcx,[rsp+38h]
  0000000140314671: call        00000001403FD860
  0000000140314676: mov         rdx,rax
  0000000140314679: lea         rcx,[rsp+30h]
  000000014031467E: movzx       r8d,r14b
  0000000140314682: call        00000001403FE840
  0000000140314687: mov         rdx,rax
  000000014031468A: lea         rcx,[rbp-59h]
  000000014031468E: call        00000001403FF710
  0000000140314693: mov         rdi,qword ptr [rbx+0000000000000CE8h]
  000000014031469A: lea         eax,[r14-31h]
  000000014031469E: movzx       eax,al
  00000001403146A1: add         rdi,108h
  00000001403146A8: imul        r15,rax,138h
  00000001403146AF: add         rdi,r15
  00000001403146B2: mov         rax,qword ptr [rdi+8]
  00000001403146B6: cmp         rax,qword ptr [rbp-59h]
  00000001403146BA: je          0000000140314752
  00000001403146C0: cmp         qword ptr [rdi],0
  00000001403146C4: je          00000001403146E2
  00000001403146C6: lea         rdx,[00000001405EB7ADh]
  00000001403146CD: lea         rcx,[rdi+8]
  00000001403146D1: call        00000001403FFB60
  00000001403146D6: test        eax,eax
  00000001403146D8: je          00000001403146E2
  00000001403146DA: mov         rcx,qword ptr [rdi]
  00000001403146DD: call        000000014001E1E0
  00000001403146E2: lea         rdx,[00000001405EB7ADh]
  00000001403146E9: lea         rcx,[rbp-59h]
  00000001403146ED: call        00000001403FFA80
  00000001403146F2: test        eax,eax
  00000001403146F4: je          0000000140314713
  00000001403146F6: lea         r8,[00000001405EB7ADh]
  00000001403146FD: mov         qword ptr [rdi],0
  0000000140314704: lea         rdx,[rbp-41h]
  0000000140314708: lea         rcx,[rdi+8]
  000000014031470C: call        00000001403FF960
  0000000140314711: jmp         0000000140314752
  0000000140314713: xor         r8d,r8d
  0000000140314716: lea         rcx,[rbp-59h]
  000000014031471A: mov         edx,3E8h
  000000014031471F: call        0000000140403790
  0000000140314724: lea         rcx,[rdi+8]
  0000000140314728: test        rax,rax
  000000014031472B: jne         0000000140314742
  000000014031472D: lea         r8,[00000001405EB7ADh]
  0000000140314734: mov         qword ptr [rdi],rax
  0000000140314737: lea         rdx,[rbp-31h]
  000000014031473B: call        00000001403FF960
  0000000140314740: jmp         0000000140314752
  0000000140314742: lea         r8,[rbp-59h]
  0000000140314746: mov         qword ptr [rdi],rax
  0000000140314749: lea         rdx,[rbp-39h]
  000000014031474D: call        00000001403FF880
  0000000140314752: lea         rcx,[rsp+30h]
  0000000140314757: call        00000001403FD740
  000000014031475C: lea         rcx,[rsp+38h]
  0000000140314761: call        00000001403FD740
  0000000140314766: lea         rcx,[rsp+40h]
  000000014031476B: call        00000001403FD740
  0000000140314770: lea         r8,[00000001405ABA80h]
  0000000140314777: mov         rdx,r13
  000000014031477A: lea         rcx,[rsp+58h]
  000000014031477F: call        00000001403FD8E0
  0000000140314784: mov         rdx,rax
  0000000140314787: lea         r8,[rsp+20h]
  000000014031478C: lea         rcx,[rsp+50h]
  0000000140314791: call        00000001403FD860
  0000000140314796: mov         rdx,rax
  0000000140314799: lea         rcx,[rsp+48h]
  000000014031479E: movzx       r8d,r14b
  00000001403147A2: call        00000001403FE840
  00000001403147A7: mov         rdx,rax
  00000001403147AA: lea         rcx,[rbp-51h]
  00000001403147AE: call        00000001403FF710
  00000001403147B3: mov         rdi,qword ptr [rbx+0000000000000CF0h]
  00000001403147BA: add         rdi,108h
  00000001403147C1: add         rdi,r15
  00000001403147C4: mov         rax,qword ptr [rdi+8]
  00000001403147C8: cmp         rax,qword ptr [rbp-51h]
  00000001403147CC: je          0000000140314864
  00000001403147D2: cmp         qword ptr [rdi],0
  00000001403147D6: je          00000001403147F4
  00000001403147D8: lea         rdx,[00000001405EB7ADh]
  00000001403147DF: lea         rcx,[rdi+8]
  00000001403147E3: call        00000001403FFB60
  00000001403147E8: test        eax,eax
  00000001403147EA: je          00000001403147F4
  00000001403147EC: mov         rcx,qword ptr [rdi]
  00000001403147EF: call        000000014001E1E0
  00000001403147F4: lea         rdx,[00000001405EB7ADh]
  00000001403147FB: lea         rcx,[rbp-51h]
  00000001403147FF: call        00000001403FFA80
  0000000140314804: test        eax,eax
  0000000140314806: je          0000000140314825
  0000000140314808: lea         r8,[00000001405EB7ADh]
  000000014031480F: mov         qword ptr [rdi],0
  0000000140314816: lea         rdx,[rbp-29h]
  000000014031481A: lea         rcx,[rdi+8]
  000000014031481E: call        00000001403FF960
  0000000140314823: jmp         0000000140314864
  0000000140314825: xor         r8d,r8d
  0000000140314828: lea         rcx,[rbp-51h]
  000000014031482C: mov         edx,3E8h
  0000000140314831: call        0000000140403790
  0000000140314836: lea         rcx,[rdi+8]
  000000014031483A: test        rax,rax
  000000014031483D: jne         0000000140314854
  000000014031483F: lea         r8,[00000001405EB7ADh]
  0000000140314846: mov         qword ptr [rdi],rax
  0000000140314849: lea         rdx,[rbp-21h]
  000000014031484D: call        00000001403FF960
  0000000140314852: jmp         0000000140314864
  0000000140314854: lea         r8,[rbp-51h]
  0000000140314858: mov         qword ptr [rdi],rax
  000000014031485B: lea         rdx,[rbp-19h]
  000000014031485F: call        00000001403FF880
  0000000140314864: lea         rcx,[rsp+48h]
  0000000140314869: call        00000001403FD740
  000000014031486E: lea         rcx,[rsp+50h]
  0000000140314873: call        00000001403FD740
  0000000140314878: lea         rcx,[rsp+58h]
  000000014031487D: call        00000001403FD740
  0000000140314882: lea         r8,[00000001405ABDC0h]
  0000000140314889: mov         rdx,r13
  000000014031488C: lea         rcx,[rbp-69h]
  0000000140314890: call        00000001403FD8E0
  0000000140314895: mov         rdx,rax
  0000000140314898: lea         r8,[rsp+20h]
  000000014031489D: lea         rcx,[rbp-71h]
  00000001403148A1: call        00000001403FD860
  00000001403148A6: mov         rdx,rax
  00000001403148A9: lea         rcx,[rbp-79h]
  00000001403148AD: movzx       r8d,r14b
  00000001403148B1: call        00000001403FE840
  00000001403148B6: mov         rdx,rax
  00000001403148B9: lea         rcx,[rbp-49h]
  00000001403148BD: call        00000001403FF710
  00000001403148C2: mov         rdi,qword ptr [rbx+0000000000000CF8h]
  00000001403148C9: add         rdi,108h
  00000001403148D0: add         rdi,r15
  00000001403148D3: mov         rax,qword ptr [rdi+8]
  00000001403148D7: cmp         rax,qword ptr [rbp-49h]
  00000001403148DB: je          0000000140314973
  00000001403148E1: cmp         qword ptr [rdi],0
  00000001403148E5: je          0000000140314903
  00000001403148E7: lea         rdx,[00000001405EB7ADh]
  00000001403148EE: lea         rcx,[rdi+8]
  00000001403148F2: call        00000001403FFB60
  00000001403148F7: test        eax,eax
  00000001403148F9: je          0000000140314903
  00000001403148FB: mov         rcx,qword ptr [rdi]
  00000001403148FE: call        000000014001E1E0
  0000000140314903: lea         rdx,[00000001405EB7ADh]
  000000014031490A: lea         rcx,[rbp-49h]
  000000014031490E: call        00000001403FFA80
  0000000140314913: test        eax,eax
  0000000140314915: je          0000000140314934
  0000000140314917: lea         r8,[00000001405EB7ADh]
  000000014031491E: mov         qword ptr [rdi],0
  0000000140314925: lea         rdx,[rbp-11h]
  0000000140314929: lea         rcx,[rdi+8]
  000000014031492D: call        00000001403FF960
  0000000140314932: jmp         0000000140314973
  0000000140314934: xor         r8d,r8d
  0000000140314937: lea         rcx,[rbp-49h]
  000000014031493B: mov         edx,3E8h
  0000000140314940: call        0000000140403790
  0000000140314945: lea         rcx,[rdi+8]
  0000000140314949: test        rax,rax
  000000014031494C: jne         0000000140314963
  000000014031494E: lea         r8,[00000001405EB7ADh]
  0000000140314955: mov         qword ptr [rdi],rax
  0000000140314958: lea         rdx,[rbp-9]
  000000014031495C: call        00000001403FF960
  0000000140314961: jmp         0000000140314973
  0000000140314963: lea         r8,[rbp-49h]
  0000000140314967: mov         qword ptr [rdi],rax
  000000014031496A: lea         rdx,[rbp-1]
  000000014031496E: call        00000001403FF880
  0000000140314973: lea         rcx,[rbp-79h]
  0000000140314977: call        00000001403FD740
  000000014031497C: lea         rcx,[rbp-71h]
  0000000140314980: call        00000001403FD740
  0000000140314985: lea         rcx,[rbp-69h]
  0000000140314989: call        00000001403FD740
  000000014031498E: mov         rax,qword ptr [rbx+0000000000000CE8h]
  0000000140314995: inc         r14b
  0000000140314998: mov         qword ptr [rax+r15+10h],rax
  000000014031499D: mov         rax,qword ptr [rbx+0000000000000CF0h]
  00000001403149A4: mov         qword ptr [rax+r15+10h],rax
  00000001403149A9: mov         rax,qword ptr [rbx+0000000000000CF8h]
  00000001403149B0: mov         qword ptr [rax+r15+10h],rax
  00000001403149B5: lea         eax,[r14-31h]
  00000001403149B9: cmp         al,byte ptr [rbx+0000000000000D59h]
  00000001403149BF: jb          0000000140314650
  00000001403149C5: mov         r14,qword ptr [rbx+0000000000000CE8h]
  00000001403149CC: xor         r15d,r15d
  00000001403149CF: cmp         dword ptr [rbx+0000000000000D60h],0
  00000001403149D6: mov         qword ptr [rbx+0000000000000CE0h],r14
  00000001403149DD: je          0000000140314E59
  00000001403149E3: cmp         dword ptr [000000014070FD18h],0
  00000001403149EA: jne         0000000140314E59
  00000001403149F0: movzx       eax,byte ptr [rbx+0000000000000D59h]
  00000001403149F7: mov         rcx,0FFFFFFFFFFFFFFFFh
  00000001403149FE: lea         rdi,[rax+rax*2]
  0000000140314A02: mov         eax,138h
  0000000140314A07: mul         rax,rdi
  0000000140314A0A: cmovo       rax,rcx
  0000000140314A0E: add         rax,8
  0000000140314A12: cmovb       rax,rcx
  0000000140314A16: mov         rcx,rax
  0000000140314A19: call        00000001404F77C4
  0000000140314A1E: test        rax,rax
  0000000140314A21: je          0000000140314A49
  0000000140314A23: mov         qword ptr [rax],rdi
  0000000140314A26: lea         r14,[rax+8]
  0000000140314A2A: mov         rsi,r14
  0000000140314A2D: test        rdi,rdi
  0000000140314A30: je          0000000140314A4C
  0000000140314A32: mov         rcx,rsi
  0000000140314A35: call        0000000140410F70
  0000000140314A3A: add         rsi,138h
  0000000140314A41: sub         rdi,1
  0000000140314A45: jne         0000000140314A32
  0000000140314A47: jmp         0000000140314A4C
  0000000140314A49: mov         r14,r15
  0000000140314A4C: movzx       ecx,byte ptr [rbx+0000000000000D59h]
  0000000140314A53: imul        rax,rcx,138h
  0000000140314A5A: mov         qword ptr [rbx+0000000000000D08h],r14
  0000000140314A61: add         rax,r14
  0000000140314A64: mov         qword ptr [rbx+0000000000000D10h],rax
  0000000140314A6B: imul        rax,rcx,270h
  0000000140314A72: add         rax,r14
  0000000140314A75: mov         qword ptr [rbx+0000000000000D18h],rax
  0000000140314A7C: test        cl,cl
  0000000140314A7E: je          0000000140314E59
  0000000140314A84: mov         r14b,31h
  0000000140314A87: nop         word ptr [rax+rax+0000000000000000h]
  0000000140314A90: lea         r8,[00000001405AB498h]
  0000000140314A97: mov         rdx,r13
  0000000140314A9A: lea         rcx,[rsp+58h]
  0000000140314A9F: call        00000001403FD8E0
  0000000140314AA4: mov         rdx,rax
  0000000140314AA7: lea         r8,[rsp+20h]
  0000000140314AAC: lea         rcx,[rbp-79h]
  0000000140314AB0: call        00000001403FD860
  0000000140314AB5: mov         rdx,rax
  0000000140314AB8: lea         rcx,[rbp-71h]
  0000000140314ABC: movzx       r8d,r14b
  0000000140314AC0: call        00000001403FE840
  0000000140314AC5: mov         rdx,rax
  0000000140314AC8: lea         r8,[0000000140608160h]
  0000000140314ACF: lea         rcx,[rbp-69h]
  0000000140314AD3: call        00000001403FD8E0
  0000000140314AD8: mov         rdx,rax
  0000000140314ADB: lea         rcx,[rbp-49h]
  0000000140314ADF: call        00000001403FF710
  0000000140314AE4: mov         rdi,qword ptr [rbx+0000000000000D08h]
  0000000140314AEB: lea         eax,[r14-31h]
  0000000140314AEF: movzx       eax,al
  0000000140314AF2: add         rdi,108h
  0000000140314AF9: imul        r15,rax,138h
  0000000140314B00: add         rdi,r15
  0000000140314B03: mov         rax,qword ptr [rdi+8]
  0000000140314B07: cmp         rax,qword ptr [rbp-49h]
  0000000140314B0B: je          0000000140314BA3
  0000000140314B11: cmp         qword ptr [rdi],0
  0000000140314B15: je          0000000140314B33
  0000000140314B17: lea         rdx,[00000001405EB7ADh]
  0000000140314B1E: lea         rcx,[rdi+8]
  0000000140314B22: call        00000001403FFB60
  0000000140314B27: test        eax,eax
  0000000140314B29: je          0000000140314B33
  0000000140314B2B: mov         rcx,qword ptr [rdi]
  0000000140314B2E: call        000000014001E1E0
  0000000140314B33: lea         rdx,[00000001405EB7ADh]
  0000000140314B3A: lea         rcx,[rbp-49h]
  0000000140314B3E: call        00000001403FFA80
  0000000140314B43: test        eax,eax
  0000000140314B45: je          0000000140314B64
  0000000140314B47: lea         r8,[00000001405EB7ADh]
  0000000140314B4E: mov         qword ptr [rdi],0
  0000000140314B55: lea         rdx,[rbp-1]
  0000000140314B59: lea         rcx,[rdi+8]
  0000000140314B5D: call        00000001403FF960
  0000000140314B62: jmp         0000000140314BA3
  0000000140314B64: xor         r8d,r8d
  0000000140314B67: lea         rcx,[rbp-49h]
  0000000140314B6B: mov         edx,3E8h
  0000000140314B70: call        0000000140403790
  0000000140314B75: lea         rcx,[rdi+8]
  0000000140314B79: test        rax,rax
  0000000140314B7C: jne         0000000140314B93
  0000000140314B7E: lea         r8,[00000001405EB7ADh]
  0000000140314B85: mov         qword ptr [rdi],rax
  0000000140314B88: lea         rdx,[rbp-9]
  0000000140314B8C: call        00000001403FF960
  0000000140314B91: jmp         0000000140314BA3
  0000000140314B93: lea         r8,[rbp-49h]
  0000000140314B97: mov         qword ptr [rdi],rax
  0000000140314B9A: lea         rdx,[rbp-11h]
  0000000140314B9E: call        00000001403FF880
  0000000140314BA3: lea         rcx,[rbp-69h]
  0000000140314BA7: call        00000001403FD740
  0000000140314BAC: lea         rcx,[rbp-71h]
  0000000140314BB0: call        00000001403FD740
  0000000140314BB5: lea         rcx,[rbp-79h]
  0000000140314BB9: call        00000001403FD740
  0000000140314BBE: lea         rcx,[rsp+58h]
  0000000140314BC3: call        00000001403FD740
  0000000140314BC8: lea         r8,[00000001405ABA80h]
  0000000140314BCF: mov         rdx,r13
  0000000140314BD2: lea         rcx,[rsp+38h]
  0000000140314BD7: call        00000001403FD8E0
  0000000140314BDC: mov         rdx,rax
  0000000140314BDF: lea         r8,[rsp+20h]
  0000000140314BE4: lea         rcx,[rsp+40h]
  0000000140314BE9: call        00000001403FD860
  0000000140314BEE: mov         rdx,rax
  0000000140314BF1: lea         rcx,[rsp+48h]
  0000000140314BF6: movzx       r8d,r14b
  0000000140314BFA: call        00000001403FE840
  0000000140314BFF: mov         rdx,rax
  0000000140314C02: lea         r8,[0000000140608160h]
  0000000140314C09: lea         rcx,[rsp+50h]
  0000000140314C0E: call        00000001403FD8E0
  0000000140314C13: mov         rdx,rax
  0000000140314C16: lea         rcx,[rbp-51h]
  0000000140314C1A: call        00000001403FF710
  0000000140314C1F: mov         rdi,qword ptr [rbx+0000000000000D10h]
  0000000140314C26: add         rdi,108h
  0000000140314C2D: add         rdi,r15
  0000000140314C30: mov         rax,qword ptr [rdi+8]
  0000000140314C34: cmp         rax,qword ptr [rbp-51h]
  0000000140314C38: je          0000000140314CD0
  0000000140314C3E: cmp         qword ptr [rdi],0
  0000000140314C42: je          0000000140314C60
  0000000140314C44: lea         rdx,[00000001405EB7ADh]
  0000000140314C4B: lea         rcx,[rdi+8]
  0000000140314C4F: call        00000001403FFB60
  0000000140314C54: test        eax,eax
  0000000140314C56: je          0000000140314C60
  0000000140314C58: mov         rcx,qword ptr [rdi]
  0000000140314C5B: call        000000014001E1E0
  0000000140314C60: lea         rdx,[00000001405EB7ADh]
  0000000140314C67: lea         rcx,[rbp-51h]
  0000000140314C6B: call        00000001403FFA80
  0000000140314C70: test        eax,eax
  0000000140314C72: je          0000000140314C91
  0000000140314C74: lea         r8,[00000001405EB7ADh]
  0000000140314C7B: mov         qword ptr [rdi],0
  0000000140314C82: lea         rdx,[rbp-19h]
  0000000140314C86: lea         rcx,[rdi+8]
  0000000140314C8A: call        00000001403FF960
  0000000140314C8F: jmp         0000000140314CD0
  0000000140314C91: xor         r8d,r8d
  0000000140314C94: lea         rcx,[rbp-51h]
  0000000140314C98: mov         edx,3E8h
  0000000140314C9D: call        0000000140403790
  0000000140314CA2: lea         rcx,[rdi+8]
  0000000140314CA6: test        rax,rax
  0000000140314CA9: jne         0000000140314CC0
  0000000140314CAB: lea         r8,[00000001405EB7ADh]
  0000000140314CB2: mov         qword ptr [rdi],rax
  0000000140314CB5: lea         rdx,[rbp-21h]
  0000000140314CB9: call        00000001403FF960
  0000000140314CBE: jmp         0000000140314CD0
  0000000140314CC0: lea         r8,[rbp-51h]
  0000000140314CC4: mov         qword ptr [rdi],rax
  0000000140314CC7: lea         rdx,[rbp-29h]
  0000000140314CCB: call        00000001403FF880
  0000000140314CD0: lea         rcx,[rsp+50h]
  0000000140314CD5: call        00000001403FD740
  0000000140314CDA: lea         rcx,[rsp+48h]
  0000000140314CDF: call        00000001403FD740
  0000000140314CE4: lea         rcx,[rsp+40h]
  0000000140314CE9: call        00000001403FD740
  0000000140314CEE: lea         rcx,[rsp+38h]
  0000000140314CF3: call        00000001403FD740
  0000000140314CF8: lea         r8,[00000001405ABDC0h]
  0000000140314CFF: mov         rdx,r13
  0000000140314D02: lea         rcx,[rbp-41h]
  0000000140314D06: call        00000001403FD8E0
  0000000140314D0B: mov         rdx,rax
  0000000140314D0E: lea         r8,[rsp+20h]
  0000000140314D13: lea         rcx,[rbp-31h]
  0000000140314D17: call        00000001403FD860
  0000000140314D1C: mov         rdx,rax
  0000000140314D1F: lea         rcx,[rbp-39h]
  0000000140314D23: movzx       r8d,r14b
  0000000140314D27: call        00000001403FE840
  0000000140314D2C: mov         rdx,rax
  0000000140314D2F: lea         r8,[0000000140608160h]
  0000000140314D36: lea         rcx,[rsp+30h]
  0000000140314D3B: call        00000001403FD8E0
  0000000140314D40: mov         rdx,rax
  0000000140314D43: lea         rcx,[rbp-59h]
  0000000140314D47: call        00000001403FF710
  0000000140314D4C: mov         rdi,qword ptr [rbx+0000000000000D18h]
  0000000140314D53: add         rdi,108h
  0000000140314D5A: add         rdi,r15
  0000000140314D5D: mov         rax,qword ptr [rdi+8]
  0000000140314D61: cmp         rax,qword ptr [rbp-59h]
  0000000140314D65: je          0000000140314DFD
  0000000140314D6B: cmp         qword ptr [rdi],0
  0000000140314D6F: je          0000000140314D8D
  0000000140314D71: lea         rdx,[00000001405EB7ADh]
  0000000140314D78: lea         rcx,[rdi+8]
  0000000140314D7C: call        00000001403FFB60
  0000000140314D81: test        eax,eax
  0000000140314D83: je          0000000140314D8D
  0000000140314D85: mov         rcx,qword ptr [rdi]
  0000000140314D88: call        000000014001E1E0
  0000000140314D8D: lea         rdx,[00000001405EB7ADh]
  0000000140314D94: lea         rcx,[rbp-59h]
  0000000140314D98: call        00000001403FFA80
  0000000140314D9D: test        eax,eax
  0000000140314D9F: je          0000000140314DBE
  0000000140314DA1: lea         r8,[00000001405EB7ADh]
  0000000140314DA8: mov         qword ptr [rdi],0
  0000000140314DAF: lea         rdx,[rbp+7]
  0000000140314DB3: lea         rcx,[rdi+8]
  0000000140314DB7: call        00000001403FF960
  0000000140314DBC: jmp         0000000140314DFD
  0000000140314DBE: xor         r8d,r8d
  0000000140314DC1: lea         rcx,[rbp-59h]
  0000000140314DC5: mov         edx,3E8h
  0000000140314DCA: call        0000000140403790
  0000000140314DCF: lea         rcx,[rdi+8]
  0000000140314DD3: test        rax,rax
  0000000140314DD6: jne         0000000140314DED
  0000000140314DD8: lea         r8,[00000001405EB7ADh]
  0000000140314DDF: mov         qword ptr [rdi],rax
  0000000140314DE2: lea         rdx,[rbp+0Fh]
  0000000140314DE6: call        00000001403FF960
  0000000140314DEB: jmp         0000000140314DFD
  0000000140314DED: lea         r8,[rbp-59h]
  0000000140314DF1: mov         qword ptr [rdi],rax
  0000000140314DF4: lea         rdx,[rbp+17h]
  0000000140314DF8: call        00000001403FF880
  0000000140314DFD: lea         rcx,[rsp+30h]
  0000000140314E02: call        00000001403FD740
  0000000140314E07: lea         rcx,[rbp-39h]
  0000000140314E0B: call        00000001403FD740
  0000000140314E10: lea         rcx,[rbp-31h]
  0000000140314E14: call        00000001403FD740
  0000000140314E19: lea         rcx,[rbp-41h]
  0000000140314E1D: call        00000001403FD740
  0000000140314E22: mov         rax,qword ptr [rbx+0000000000000D08h]
  0000000140314E29: inc         r14b
  0000000140314E2C: mov         qword ptr [rax+r15+10h],rax
  0000000140314E31: mov         rax,qword ptr [rbx+0000000000000D10h]
  0000000140314E38: mov         qword ptr [rax+r15+10h],rax
  0000000140314E3D: mov         rax,qword ptr [rbx+0000000000000D18h]
  0000000140314E44: mov         qword ptr [rax+r15+10h],rax
  0000000140314E49: lea         eax,[r14-31h]
  0000000140314E4D: cmp         al,byte ptr [rbx+0000000000000D59h]
  0000000140314E53: jb          0000000140314A90
  0000000140314E59: cmp         dword ptr [rbx+0000000000000D54h],0
  0000000140314E60: mov         rax,qword ptr [rbx+0000000000000D08h]
  0000000140314E67: mov         qword ptr [rbx+0000000000000D00h],rax
  0000000140314E6E: mov         rax,qword ptr [rbx+0000000000000CE0h]
  0000000140314E75: mov         qword ptr [rbx+0000000000000CD8h],rax
  0000000140314E7C: je          0000000140314F6A
  0000000140314E82: mov         rsi,qword ptr [rbp-61h]
  0000000140314E86: xor         dil,dil
  0000000140314E89: nop         dword ptr [rax+0000000000000000h]
  0000000140314E90: mov         rax,qword ptr [0000000140667548h]
  0000000140314E97: mov         rcx,r12
  0000000140314E9A: movzx       r8d,byte ptr [rsi]
  0000000140314E9E: movzx       edx,dil
  0000000140314EA2: mov         r9,qword ptr [rax+0000000000001090h]
  0000000140314EA9: add         r9,63D8h
  0000000140314EB0: call        00000001404221C0
  0000000140314EB5: inc         dil
  0000000140314EB8: inc         rsi
  0000000140314EBB: cmp         dil,7
  0000000140314EBF: jb          0000000140314E90
  0000000140314EC1: xor         sil,sil
  0000000140314EC4: cmp         byte ptr [rbx+0000000000000D59h],sil
  0000000140314ECB: jbe         0000000140314F6A
  0000000140314ED1: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  0000000140314ED8: mov         rdx,r12
  0000000140314EDB: movzx       eax,sil
  0000000140314EDF: imul        rdi,rax,138h
  0000000140314EE6: add         rcx,rdi
  0000000140314EE9: call        0000000140412390
  0000000140314EEE: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  0000000140314EF5: mov         rdx,r12
  0000000140314EF8: add         rcx,rdi
  0000000140314EFB: call        0000000140412390
  0000000140314F00: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  0000000140314F07: mov         rdx,r12
  0000000140314F0A: add         rcx,rdi
  0000000140314F0D: call        0000000140412390
  0000000140314F12: cmp         dword ptr [rbx+0000000000000D60h],0
  0000000140314F19: je          0000000140314F5A
  0000000140314F1B: cmp         dword ptr [000000014070FD18h],0
  0000000140314F22: jne         0000000140314F5A
  0000000140314F24: mov         rcx,qword ptr [rbx+0000000000000D08h]
  0000000140314F2B: mov         rdx,r12
  0000000140314F2E: add         rcx,rdi
  0000000140314F31: call        0000000140412390
  0000000140314F36: mov         rcx,qword ptr [rbx+0000000000000D10h]
  0000000140314F3D: mov         rdx,r12
  0000000140314F40: add         rcx,rdi
  0000000140314F43: call        0000000140412390
  0000000140314F48: mov         rcx,qword ptr [rbx+0000000000000D18h]
  0000000140314F4F: mov         rdx,r12
  0000000140314F52: add         rcx,rdi
  0000000140314F55: call        0000000140412390
  0000000140314F5A: inc         sil
  0000000140314F5D: cmp         sil,byte ptr [rbx+0000000000000D59h]
  0000000140314F64: jb          0000000140314ED1
  0000000140314F6A: cmp         dword ptr [rbx+0000000000000D60h],0
  0000000140314F71: mov         eax,1
  0000000140314F76: mov         word ptr [rbx+0000000000000D50h],ax
  0000000140314F7D: jne         0000000140315050
  0000000140314F83: movzx       eax,byte ptr [00000001405ACE93h]
  0000000140314F8A: cmp         byte ptr [rbx+0000000000000D58h],al
  0000000140314F90: je          0000000140315050
  0000000140314F96: cmp         dword ptr [rbx+0000000000000D54h],0
  0000000140314F9D: je          0000000140314FBE
  0000000140314F9F: movzx       r8d,byte ptr [00000001405C067Ah]
  0000000140314FA7: lea         rdx,[rbp-59h]
  0000000140314FAB: mov         r9d,0FF00h
  0000000140314FB1: mov         rcx,r12
  0000000140314FB4: call        0000000140422180
  0000000140314FB9: jmp         0000000140315050
  0000000140314FBE: xor         dl,dl
  0000000140314FC0: cmp         byte ptr [rbx+0000000000000D59h],dl
  0000000140314FC6: jbe         0000000140315050
  0000000140314FCC: nop         dword ptr [rax]
  0000000140314FD0: movzx       eax,dl
  0000000140314FD3: imul        rcx,rax,138h
  0000000140314FDA: mov         rax,qword ptr [rbx+0000000000000CE8h]
  0000000140314FE1: mov         byte ptr [rcx+rax+0000000000000130h],0
  0000000140314FE9: mov         rax,qword ptr [rbx+0000000000000CF0h]
  0000000140314FF0: mov         byte ptr [rax+rcx+0000000000000130h],0
  0000000140314FF8: mov         rax,qword ptr [rbx+0000000000000CF8h]
  0000000140314FFF: mov         byte ptr [rcx+rax+0000000000000130h],0
  0000000140315007: cmp         dword ptr [rbx+0000000000000D60h],0
  000000014031500E: je          0000000140315046
  0000000140315010: cmp         dword ptr [000000014070FD18h],0
  0000000140315017: jne         0000000140315046
  0000000140315019: mov         rax,qword ptr [rbx+0000000000000D08h]
  0000000140315020: mov         byte ptr [rax+rcx+0000000000000130h],0
  0000000140315028: mov         rax,qword ptr [rbx+0000000000000D10h]
  000000014031502F: mov         byte ptr [rax+rcx+0000000000000130h],0
  0000000140315037: mov         rax,qword ptr [rbx+0000000000000D18h]
  000000014031503E: mov         byte ptr [rax+rcx+0000000000000130h],0
  0000000140315046: inc         dl
  0000000140315048: cmp         dl,byte ptr [rbx+0000000000000D59h]
  000000014031504E: jb          0000000140314FD0
  0000000140315050: cmp         dword ptr [rbx+0000000000000D60h],0
  0000000140315057: movzx       eax,word ptr [rsp+28h]
  000000014031505C: mov         word ptr [rbx+0000000000000D52h],ax
  0000000140315063: je          0000000140315086
  0000000140315065: cmp         dword ptr [000000014070FD18h],0
  000000014031506C: jne         0000000140315086
  000000014031506E: movzx       ecx,ax
  0000000140315071: movzx       eax,byte ptr [rbx+0000000000000D58h]
  0000000140315078: cmp         cx,ax
  000000014031507B: jle         0000000140315086
  000000014031507D: mov         rax,qword ptr [rbx+0000000000000D00h]
  0000000140315084: jmp         000000014031508D
  0000000140315086: mov         rax,qword ptr [rbx+0000000000000CE0h]
  000000014031508D: mov         qword ptr [rbx+0000000000000CD8h],rax
  0000000140315094: cmp         dword ptr [rbx+0000000000000D60h],0
  000000014031509B: je          00000001403150AA
  000000014031509D: cmp         dword ptr [000000014070FD18h],0
  00000001403150A4: je          00000001403151B0
  00000001403150AA: movzx       ecx,byte ptr [rbx+0000000000000D58h]
  00000001403150B1: cmp         word ptr [rbx+0000000000000D52h],cx
  00000001403150B8: jle         00000001403151B0
  00000001403150BE: mov         rax,qword ptr [rbx+0000000000000CE8h]
  00000001403150C5: cmp         qword ptr [rbx+0000000000000CE0h],rax
  00000001403150CC: jne         00000001403150D8
  00000001403150CE: cmp         word ptr [rbx+0000000000000D50h],0
  00000001403150D6: je          00000001403150E0
  00000001403150D8: cmp         cl,byte ptr [00000001405ACE93h]
  00000001403150DE: jne         0000000140315143
  00000001403150E0: xor         dil,dil
  00000001403150E3: cmp         byte ptr [rbx+0000000000000D59h],dil
  00000001403150EA: jbe         00000001403151F5
  00000001403150F0: movsx       eax,word ptr [rbx+0000000000000D52h]
  00000001403150F7: mov         edx,10h
  00000001403150FC: sub         edx,eax
  00000001403150FE: and         edx,8000000Fh
  0000000140315104: jge         000000014031510D
  0000000140315106: dec         edx
  0000000140315108: or          edx,0FFFFFFF0h
  000000014031510B: inc         edx
  000000014031510D: movzx       eax,word ptr [rbx+0000000000000D50h]
  0000000140315114: shl         ax,4
  0000000140315118: add         dx,ax
  000000014031511B: movzx       eax,dil
  000000014031511F: imul        rcx,rax,138h
  0000000140315126: add         rcx,qword ptr [rbx+0000000000000CD8h]
  000000014031512D: call        0000000140412380
  0000000140315132: inc         dil
  0000000140315135: cmp         dil,byte ptr [rbx+0000000000000D59h]
  000000014031513C: jb          00000001403150F0
  000000014031513E: jmp         00000001403151F5
  0000000140315143: xor         dil,dil
  0000000140315146: cmp         byte ptr [rbx+0000000000000D59h],dil
  000000014031514D: jbe         00000001403151F5
  0000000140315153: nop         dword ptr [rax]
  0000000140315157: nop         word ptr [rax+rax+0000000000000000h]
  0000000140315160: movsx       eax,word ptr [rbx+0000000000000D52h]
  0000000140315167: mov         edx,11h
  000000014031516C: sub         edx,eax
  000000014031516E: and         edx,8000000Fh
  0000000140315174: jge         000000014031517D
  0000000140315176: dec         edx
  0000000140315178: or          edx,0FFFFFFF0h
  000000014031517B: inc         edx
  000000014031517D: movzx       eax,word ptr [rbx+0000000000000D50h]
  0000000140315184: shl         ax,4
  0000000140315188: add         dx,ax
  000000014031518B: movzx       eax,dil
  000000014031518F: imul        rcx,rax,138h
  0000000140315196: add         rcx,qword ptr [rbx+0000000000000CD8h]
  000000014031519D: call        0000000140412380
  00000001403151A2: inc         dil
  00000001403151A5: cmp         dil,byte ptr [rbx+0000000000000D59h]
  00000001403151AC: jb          0000000140315160
  00000001403151AE: jmp         00000001403151F5
  00000001403151B0: xor         dil,dil
  00000001403151B3: cmp         byte ptr [rbx+0000000000000D59h],dil
  00000001403151BA: jbe         00000001403151F5
  00000001403151BC: nop         dword ptr [rax]
  00000001403151C0: movzx       edx,word ptr [rbx+0000000000000D50h]
  00000001403151C7: movzx       eax,dil
  00000001403151CB: imul        rcx,rax,138h
  00000001403151D2: shl         dx,4
  00000001403151D6: add         rcx,qword ptr [rbx+0000000000000CD8h]
  00000001403151DD: add         dx,word ptr [rbx+0000000000000D52h]
  00000001403151E4: call        0000000140412380
  00000001403151E9: inc         dil
  00000001403151EC: cmp         dil,byte ptr [rbx+0000000000000D59h]
  00000001403151F3: jb          00000001403151C0
  00000001403151F5: lea         rcx,[rsp+20h]
  00000001403151FA: call        00000001403FD740
  00000001403151FF: mov         rax,rbx
  0000000140315202: mov         rcx,qword ptr [rbp+1Fh]
  0000000140315206: xor         rcx,rsp
  0000000140315209: call        00000001404F77A0
  000000014031520E: mov         rbx,qword ptr [rsp+0000000000000158h]
  0000000140315216: add         rsp,100h
  000000014031521D: pop         r15
  000000014031521F: pop         r14
  0000000140315221: pop         r13
  0000000140315223: pop         r12
  0000000140315225: pop         rdi
  0000000140315226: pop         rsi
  0000000140315227: pop         rbp
  0000000140315228: ret
  0000000140315229: int         3
  000000014031522A: int         3
  000000014031522B: int         3
  000000014031522C: int         3
  000000014031522D: int         3
  000000014031522E: int         3
  000000014031522F: int         3
  0000000140315230: mov         qword ptr [rsp+20h],rbx
  0000000140315235: push        rbp
  0000000140315236: push        rsi
  0000000140315237: push        rdi
  0000000140315238: push        r12
  000000014031523A: push        r13
  000000014031523C: push        r14
  000000014031523E: push        r15
  0000000140315240: lea         rbp,[rsp-27h]
  0000000140315245: sub         rsp,0C0h
  000000014031524C: mov         rax,qword ptr [00000001406649D8h]
  0000000140315253: xor         rax,rsp
  0000000140315256: mov         qword ptr [rbp+17h],rax
  000000014031525A: mov         word ptr [rbp-71h],r9w
  000000014031525F: mov         r14,r8
  0000000140315262: movzx       r15d,dx
  0000000140315266: mov         rbx,rcx
  0000000140315269: call        00000001403074D0
  000000014031526E: lea         rax,[00000001405A92E0h]
  0000000140315275: lea         r13,[rbx+0000000000000CE0h]
  000000014031527C: mov         qword ptr [rbx],rax
  000000014031527F: mov         rcx,r13
  0000000140315282: call        0000000140410F70
  0000000140315287: movzx       edx,word ptr [00000001405C067Ch]
  000000014031528E: lea         rcx,[rbx+0000000000000E18h]
  0000000140315295: call        0000000140421010
  000000014031529A: mov         word ptr [rbx+8],r15w
  000000014031529F: lea         rcx,[00000001405AB1F8h]
  00000001403152A6: mov         dword ptr [rbx+0000000000000E4Ch],1
  00000001403152B0: mov         edi,0Ah
  00000001403152B5: mov         byte ptr [rbx+0000000000000E50h],1
  00000001403152BC: mov         edx,r15d
  00000001403152BF: mov         dword ptr [rbx+48h],edi
  00000001403152C2: mov         esi,r15d
  00000001403152C5: mov         dword ptr [rbx+30h],0A0000h
  00000001403152CC: mov         dword ptr [rbx+34h],0AFFF6h
  00000001403152D3: mov         dword ptr [rbx+38h],0FFF6h
  00000001403152DA: mov         dword ptr [rbx+3Ch],0FFF6FFF6h
  00000001403152E1: mov         dword ptr [rbx+40h],0FFF60000h
  00000001403152E8: mov         dword ptr [rbx+44h],0FFF6000Ah
  00000001403152EF: mov         dword ptr [rbx+4Ch],0A000Ah
  00000001403152F6: call        0000000140400170
  00000001403152FB: mov         rdx,rax
  00000001403152FE: lea         rcx,[rbp-9]
  0000000140315302: call        00000001403FF7C0
  0000000140315307: mov         edx,edi
  0000000140315309: mov         rcx,qword ptr [rax]
  000000014031530C: mov         qword ptr [rbp+7],rcx
  0000000140315310: lea         rcx,[rbp-59h]
  0000000140315314: call        00000001404073A0
  0000000140315319: lea         rax,[0000000140590938h]
  0000000140315320: lea         rdx,[00000001405EB7ADh]
  0000000140315327: mov         qword ptr [rbp-59h],rax
  000000014031532B: lea         rcx,[rbp-21h]
  000000014031532F: call        00000001403FD6B0
  0000000140315334: lea         rdx,[rbp-1]
  0000000140315338: mov         qword ptr [rbp-19h],0
  0000000140315340: lea         rcx,[rbp+7]
  0000000140315344: call        00000001403FFF70
  0000000140315349: mov         rdx,rax
  000000014031534C: lea         rcx,[rbp-59h]
  0000000140315350: call        0000000140306FC0
  0000000140315355: lea         rcx,[rbp-1]
  0000000140315359: call        00000001403FD740
  000000014031535E: lea         rdx,[00000001405ABDF8h]
  0000000140315365: lea         rcx,[rbp-69h]
  0000000140315369: call        00000001403FD6B0
  000000014031536E: lea         rdx,[rbp-69h]
  0000000140315372: lea         rcx,[rbp-59h]
  0000000140315376: call        0000000140306F50
  000000014031537B: lea         rcx,[rbp-69h]
  000000014031537F: mov         rdi,rax
  0000000140315382: call        00000001403FD740
  0000000140315387: mov         rdx,rdi
  000000014031538A: mov         rcx,rbx
  000000014031538D: call        000000014033E450
  0000000140315392: test        al,al
  0000000140315394: je          00000001403153C8
  0000000140315396: lea         rdx,[00000001405AC7D0h]
  000000014031539D: lea         rcx,[rbp-61h]
  00000001403153A1: call        00000001403FD6B0
  00000001403153A6: lea         rdx,[rbp-61h]
  00000001403153AA: lea         rcx,[rbp-59h]
  00000001403153AE: call        0000000140306F50
  00000001403153B3: lea         rcx,[rbp-61h]
  00000001403153B7: mov         rdi,rax
  00000001403153BA: call        00000001403FD740
  00000001403153BF: test        rdi,rdi
  00000001403153C2: jne         00000001403155EA
  00000001403153C8: lea         rax,[0000000140590938h]
  00000001403153CF: lea         rcx,[rbp-59h]
  00000001403153D3: mov         qword ptr [rbp-59h],rax
  00000001403153D7: call        0000000140306E80
  00000001403153DC: lea         rcx,[rbp-21h]
  00000001403153E0: call        00000001403FD740
  00000001403153E5: lea         rcx,[rbp-59h]
  00000001403153E9: call        00000001404073D0
  00000001403153EE: mov         rax,qword ptr [000000014065CB10h]
  00000001403153F5: mov         qword ptr [rbp-79h],rax
  00000001403153F9: mov         eax,esi
  00000001403153FB: and         eax,0F00h
  0000000140315400: cmp         eax,400h
  0000000140315405: ja          0000000140315555
  000000014031540B: je          000000014031553D
  0000000140315411: test        eax,eax
  0000000140315413: je          00000001403154F3
  0000000140315419: cmp         eax,100h
  000000014031541E: je          0000000140315481
  0000000140315420: cmp         eax,200h
  0000000140315425: je          0000000140315465
  0000000140315427: cmp         eax,300h
  000000014031542C: jne         00000001403155B6
  0000000140315432: lea         rdx,[00000001405AB4ECh]
  0000000140315439: lea         rcx,[rbp-79h]
  000000014031543D: call        00000001403FD810
  0000000140315442: mov         dword ptr [rbx+0000000000000E4Ch],0
  000000014031544C: mov         byte ptr [rbx+00000000000005F0h],5
  0000000140315453: mov         word ptr [rbx+21h],0FF2Dh
  0000000140315459: mov         byte ptr [rbx+0000000000000E50h],0
  0000000140315460: jmp         00000001403155AB
  0000000140315465: lea         rdx,[00000001405AB4E4h]
  000000014031546C: lea         rcx,[rbp-79h]
  0000000140315470: call        00000001403FD810
  0000000140315475: mov         byte ptr [rbx+0000000000000E50h],0
  000000014031547C: jmp         00000001403155AB
  0000000140315481: and         esi,0Fh
  0000000140315484: je          00000001403154B5
  0000000140315486: sub         esi,1
  0000000140315489: je          00000001403154A8
  000000014031548B: cmp         esi,1
  000000014031548E: jne         0000000140315475
  0000000140315490: test        r15b,0F0h
  0000000140315494: lea         rax,[00000001405AB4DCh]
  000000014031549B: lea         rdx,[00000001405AB4D4h]
  00000001403154A2: cmovne      rdx,rax
  00000001403154A6: jmp         000000014031546C
  00000001403154A8: mov         byte ptr [rbx+22h],0FFh
  00000001403154AC: lea         rdx,[00000001405AB4CCh]
  00000001403154B3: jmp         000000014031546C
  00000001403154B5: mov         byte ptr [rbx+22h],0FFh
  00000001403154B9: lea         rcx,[rbp-79h]
  00000001403154BD: test        r15b,0F0h
  00000001403154C1: jne         00000001403154DB
  00000001403154C3: lea         rdx,[00000001405AB4BCh]
  00000001403154CA: call        00000001403FD810
  00000001403154CF: mov         byte ptr [rbx+0000000000000E50h],0
  00000001403154D6: jmp         00000001403155AB
  00000001403154DB: lea         rdx,[00000001405AB4C4h]
  00000001403154E2: call        00000001403FD810
  00000001403154E7: mov         byte ptr [rbx+0000000000000E50h],0
  00000001403154EE: jmp         00000001403155AB
  00000001403154F3: and         esi,0Fh
  00000001403154F6: je          000000014031551C
  00000001403154F8: cmp         esi,2
  00000001403154FB: jne         0000000140315475
  0000000140315501: test        r15b,0F0h
  0000000140315505: lea         rax,[00000001405AB4B4h]
  000000014031550C: lea         rdx,[00000001405AB4ACh]
  0000000140315513: cmovne      rdx,rax
  0000000140315517: jmp         000000014031546C
  000000014031551C: mov         byte ptr [rbx+22h],0FFh
  0000000140315520: lea         rdx,[00000001405AB49Ch]
  0000000140315527: test        r15b,0F0h
  000000014031552B: je          000000014031546C
  0000000140315531: lea         rdx,[00000001405AB4A4h]
  0000000140315538: jmp         000000014031546C
  000000014031553D: test        r15b,0F0h
  0000000140315541: lea         rax,[00000001405AB4FCh]
  0000000140315548: lea         rdx,[00000001405AB4F4h]
  000000014031554F: cmovne      rdx,rax
  0000000140315553: jmp         00000001403155A2
  0000000140315555: cmp         eax,500h
  000000014031555A: je          000000014031559B
  000000014031555C: cmp         eax,600h
  0000000140315561: je          0000000140315592
  0000000140315563: cmp         eax,700h
  0000000140315568: je          000000014031557A
  000000014031556A: cmp         eax,800h
  000000014031556F: jne         00000001403155B6
  0000000140315571: lea         rdx,[00000001405AB524h]
  0000000140315578: jmp         00000001403155A2
  000000014031557A: test        r15b,0F0h
  000000014031557E: lea         rax,[00000001405AB51Ch]
  0000000140315585: lea         rdx,[00000001405AB514h]
  000000014031558C: cmovne      rdx,rax
  0000000140315590: jmp         00000001403155A2
  0000000140315592: lea         rdx,[00000001405AB50Ch]
  0000000140315599: jmp         00000001403155A2
  000000014031559B: lea         rdx,[00000001405AB504h]
  00000001403155A2: lea         rcx,[rbp-79h]
  00000001403155A6: call        00000001403FD810
  00000001403155AB: lea         rax,[00000001405EB7ADh]
  00000001403155B2: mov         qword ptr [rbx+28h],rax
  00000001403155B6: lea         rdx,[rbp-79h]
  00000001403155BA: lea         rcx,[rbp-1]
  00000001403155BE: call        00000001403FF710
  00000001403155C3: mov         r9d,1
  00000001403155C9: lea         rcx,[rbx+0000000000000DE8h]
  00000001403155D0: mov         r8d,r9d
  00000001403155D3: lea         rdx,[rbp-1]
  00000001403155D7: call        000000014014D080
  00000001403155DC: lea         rcx,[rbp-79h]
  00000001403155E0: call        00000001403FD740
  00000001403155E5: jmp         00000001403156BB
  00000001403155EA: mov         rsi,qword ptr [rdi+8]
  00000001403155EE: test        rsi,rsi
  00000001403155F1: je          0000000140315695
  00000001403155F7: nop         word ptr [rax+rax+0000000000000000h]
  0000000140315600: mov         rdi,qword ptr [rsi+10h]
  0000000140315604: lea         rcx,[rbp-79h]
  0000000140315608: lea         rdx,[rdi+8]
  000000014031560C: call        00000001403FD640
  0000000140315611: lea         rcx,[rbp-79h]
  0000000140315615: call        00000001403FE650
  000000014031561A: mov         rcx,qword ptr [rbp-79h]
  000000014031561E: call        000000014043F480
  0000000140315623: cmp         eax,52534552h
  0000000140315628: je          000000014031565A
  000000014031562A: cmp         eax,534C4146h
  000000014031562F: je          0000000140315649
  0000000140315631: cmp         eax,5F4E4143h
  0000000140315636: jne         0000000140315680
  0000000140315638: mov         rcx,qword ptr [rdi+10h]
  000000014031563C: call        0000000140503D20
  0000000140315641: mov         byte ptr [rbx+0000000000000E50h],al
  0000000140315647: jmp         0000000140315680
  0000000140315649: mov         rcx,qword ptr [rdi+10h]
  000000014031564D: call        0000000140503D20
  0000000140315652: mov         dword ptr [rbx+0000000000000E4Ch],eax
  0000000140315658: jmp         0000000140315680
  000000014031565A: lea         rdx,[rdi+10h]
  000000014031565E: lea         rcx,[rbp+0Fh]
  0000000140315662: call        00000001403FF710
  0000000140315667: mov         r9d,1
  000000014031566D: lea         rcx,[rbx+0000000000000DE8h]
  0000000140315674: mov         r8d,r9d
  0000000140315677: lea         rdx,[rbp+0Fh]
  000000014031567B: call        000000014014D080
  0000000140315680: lea         rcx,[rbp-79h]
  0000000140315684: call        00000001403FD740
  0000000140315689: mov         rsi,qword ptr [rsi]
  000000014031568C: test        rsi,rsi
  000000014031568F: jne         0000000140315600
  0000000140315695: lea         rax,[0000000140590938h]
  000000014031569C: lea         rcx,[rbp-59h]
  00000001403156A0: mov         qword ptr [rbp-59h],rax
  00000001403156A4: call        0000000140306E80
  00000001403156A9: lea         rcx,[rbp-21h]
  00000001403156AD: call        00000001403FD740
  00000001403156B2: lea         rcx,[rbp-59h]
  00000001403156B6: call        00000001404073D0
  00000001403156BB: mov         rcx,rbx
  00000001403156BE: call        0000000140316900
  00000001403156C3: cmp         dword ptr [rbx+0000000000000E4Ch],0
  00000001403156CA: mov         qword ptr [rbx+0000000000000CD8h],r13
  00000001403156D1: mov         qword ptr [rbx+0000000000000CD0h],r13
  00000001403156D8: je          0000000140315725
  00000001403156DA: xor         dil,dil
  00000001403156DD: nop         dword ptr [rax]
  00000001403156E0: mov         rax,qword ptr [0000000140667548h]
  00000001403156E7: lea         rcx,[rbx+0000000000000E18h]
  00000001403156EE: movzx       r8d,byte ptr [r14]
  00000001403156F2: movzx       edx,dil
  00000001403156F6: mov         r9,qword ptr [rax+0000000000001090h]
  00000001403156FD: add         r9,63D8h
  0000000140315704: call        00000001404221C0
  0000000140315709: inc         dil
  000000014031570C: lea         r14,[r14+1]
  0000000140315710: cmp         dil,7
  0000000140315714: jb          00000001403156E0
  0000000140315716: lea         rdx,[rbx+0000000000000E18h]
  000000014031571D: mov         rcx,r13
  0000000140315720: call        0000000140412390
  0000000140315725: xor         eax,eax
  0000000140315727: mov         word ptr [rbx+0000000000000E48h],ax
  000000014031572E: movzx       eax,word ptr [rbp-71h]
  0000000140315732: mov         word ptr [rbx+0000000000000E4Ah],ax
  0000000140315739: mov         rax,rbx
  000000014031573C: mov         rcx,qword ptr [rbp+17h]
  0000000140315740: xor         rcx,rsp
  0000000140315743: call        00000001404F77A0
  0000000140315748: mov         rbx,qword ptr [rsp+0000000000000118h]
  0000000140315750: add         rsp,0C0h
  0000000140315757: pop         r15
  0000000140315759: pop         r14
  000000014031575B: pop         r13
  000000014031575D: pop         r12
  000000014031575F: pop         rdi
  0000000140315760: pop         rsi
  0000000140315761: pop         rbp
  0000000140315762: ret
  0000000140315763: int         3
  0000000140315764: int         3
  0000000140315765: int         3
  0000000140315766: int         3
  0000000140315767: int         3
  0000000140315768: int         3
  0000000140315769: int         3
  000000014031576A: int         3
  000000014031576B: int         3
  000000014031576C: int         3
  000000014031576D: int         3
  000000014031576E: int         3
  000000014031576F: int         3
  0000000140315770: mov         qword ptr [rsp+8],rbx
  0000000140315775: mov         qword ptr [rsp+10h],rsi
  000000014031577A: push        rdi
  000000014031577B: sub         rsp,20h
  000000014031577F: lea         rax,[00000001405A8D10h]
  0000000140315786: mov         rsi,rcx
  0000000140315789: mov         qword ptr [rcx],rax
  000000014031578C: add         rcx,0BB0h
  0000000140315793: call        00000001404111A0
  0000000140315798: mov         ebx,14h
  000000014031579D: lea         rdi,[rsi+0000000000000BA8h]
  00000001403157A4: sub         rdi,48h
  00000001403157A8: mov         rcx,rdi
  00000001403157AB: call        000000014024EAA0
  00000001403157B0: sub         rbx,1
  00000001403157B4: jne         00000001403157A4
  00000001403157B6: lea         rcx,[rsi+0000000000000600h]
  00000001403157BD: call        00000001403FD740
  00000001403157C2: lea         edi,[rbx+5]
  00000001403157C5: lea         rbx,[rsi+00000000000005F0h]
  00000001403157CC: nop         dword ptr [rax]
  00000001403157D0: sub         rbx,120h
  00000001403157D7: mov         rcx,rbx
  00000001403157DA: call        00000001404111A0
  00000001403157DF: sub         rdi,1
  00000001403157E3: jne         00000001403157D0
  00000001403157E5: mov         rbx,qword ptr [rsp+30h]
  00000001403157EA: mov         rsi,qword ptr [rsp+38h]
  00000001403157EF: add         rsp,20h
  00000001403157F3: pop         rdi
  00000001403157F4: ret
  00000001403157F5: int         3
  00000001403157F6: int         3
  00000001403157F7: int         3
  00000001403157F8: int         3
  00000001403157F9: int         3
  00000001403157FA: int         3
  00000001403157FB: int         3
  00000001403157FC: int         3
  00000001403157FD: int         3
  00000001403157FE: int         3
  00000001403157FF: int         3
  0000000140315800: push        rbx
  0000000140315802: sub         rsp,20h
  0000000140315806: mov         rbx,rcx
  0000000140315809: add         rcx,5150h
  0000000140315810: call        0000000140411200
  0000000140315815: lea         rcx,[rbx+0000000000005018h]
  000000014031581C: call        0000000140411200
  0000000140315821: lea         rcx,[rbx+0000000000004EE0h]
  0000000140315828: call        0000000140411200
  000000014031582D: lea         rcx,[rbx+0000000000004DA8h]
  0000000140315834: call        0000000140411200
  0000000140315839: lea         rcx,[rbx+0000000000004C70h]
  0000000140315840: call        0000000140411200
  0000000140315845: lea         rcx,[rbx+0000000000004B38h]
  000000014031584C: call        0000000140411200
  0000000140315851: lea         rcx,[rbx+0000000000004A00h]
  0000000140315858: call        0000000140411200
  000000014031585D: lea         rcx,[rbx+00000000000048C8h]
  0000000140315864: call        0000000140411200
  0000000140315869: lea         rcx,[rbx+0000000000004790h]
  0000000140315870: call        0000000140411200
  0000000140315875: lea         rcx,[rbx+0000000000004658h]
  000000014031587C: call        0000000140411200
  0000000140315881: lea         rcx,[rbx+0000000000004520h]
  0000000140315888: call        0000000140411200
  000000014031588D: lea         rcx,[rbx+00000000000043E8h]
  0000000140315894: call        0000000140411200
  0000000140315899: lea         rcx,[rbx+00000000000043A0h]
  00000001403158A0: call        0000000140421100
  00000001403158A5: lea         rcx,[rbx+0000000000004268h]
  00000001403158AC: call        0000000140411200
  00000001403158B1: lea         rcx,[rbx+0000000000004130h]
  00000001403158B8: call        0000000140411200
  00000001403158BD: lea         rcx,[rbx+0000000000003FF8h]
  00000001403158C4: call        0000000140411200
  00000001403158C9: lea         rcx,[rbx+0000000000003EC0h]
  00000001403158D0: call        0000000140411200
  00000001403158D5: lea         rcx,[rbx+0000000000003D88h]
  00000001403158DC: call        0000000140411200
  00000001403158E1: lea         rcx,[rbx+0000000000003C50h]
  00000001403158E8: call        0000000140411200
  00000001403158ED: lea         rcx,[rbx+0000000000003B18h]
  00000001403158F4: call        0000000140411200
  00000001403158F9: lea         rcx,[rbx+00000000000039E0h]
  0000000140315900: call        0000000140411200
  0000000140315905: lea         rcx,[rbx+00000000000038A8h]
  000000014031590C: call        0000000140411200
  0000000140315911: lea         rcx,[rbx+0000000000003770h]
  0000000140315918: call        0000000140411200
  000000014031591D: lea         rcx,[rbx+0000000000003638h]
  0000000140315924: call        0000000140411200
  0000000140315929: lea         rcx,[rbx+0000000000003500h]
  0000000140315930: call        0000000140411200
  0000000140315935: lea         rcx,[rbx+00000000000034E0h]
  000000014031593C: call        00000001403FD740
  0000000140315941: lea         rcx,[rbx+00000000000034B0h]
  0000000140315948: call        0000000140421100
  000000014031594D: lea         rcx,[rbx+0000000000003378h]
  0000000140315954: call        0000000140411200
  0000000140315959: lea         rcx,[rbx+0000000000003240h]
  0000000140315960: call        0000000140411200
  0000000140315965: lea         rcx,[rbx+0000000000003108h]
  000000014031596C: call        0000000140411200
  0000000140315971: lea         rcx,[rbx+0000000000002FD0h]
  0000000140315978: call        0000000140411200
  000000014031597D: lea         rcx,[rbx+0000000000002E98h]
  0000000140315984: call        0000000140411200
  0000000140315989: lea         rcx,[rbx+0000000000002D60h]
  0000000140315990: call        0000000140411200
  0000000140315995: lea         rcx,[rbx+0000000000002C28h]
  000000014031599C: call        0000000140411200
  00000001403159A1: lea         rcx,[rbx+0000000000002AF0h]
  00000001403159A8: call        0000000140411200
  00000001403159AD: lea         rcx,[rbx+00000000000029B8h]
  00000001403159B4: call        0000000140411200
  00000001403159B9: lea         rcx,[rbx+0000000000002880h]
  00000001403159C0: call        0000000140411200
  00000001403159C5: lea         rcx,[rbx+0000000000002860h]
  00000001403159CC: call        00000001403FD740
  00000001403159D1: lea         rcx,[rbx+0000000000002830h]
  00000001403159D8: call        0000000140421100
  00000001403159DD: lea         rcx,[rbx+00000000000026F8h]
  00000001403159E4: call        0000000140411200
  00000001403159E9: lea         rcx,[rbx+00000000000025C0h]
  00000001403159F0: call        0000000140411200
  00000001403159F5: lea         rcx,[rbx+0000000000002488h]
  00000001403159FC: call        0000000140411200
  0000000140315A01: lea         rcx,[rbx+0000000000002350h]
  0000000140315A08: call        0000000140411200
  0000000140315A0D: lea         rcx,[rbx+0000000000002218h]
  0000000140315A14: call        0000000140411200
  0000000140315A19: lea         rcx,[rbx+00000000000020E0h]
  0000000140315A20: call        0000000140411200
  0000000140315A25: lea         rcx,[rbx+0000000000001FA8h]
  0000000140315A2C: call        0000000140411200
  0000000140315A31: lea         rcx,[rbx+0000000000001E70h]
  0000000140315A38: call        0000000140411200
  0000000140315A3D: lea         rcx,[rbx+0000000000001D38h]
  0000000140315A44: call        0000000140411200
  0000000140315A49: lea         rcx,[rbx+0000000000001C00h]
  0000000140315A50: call        0000000140411200
  0000000140315A55: lea         rcx,[rbx+0000000000001BE0h]
  0000000140315A5C: call        00000001403FD740
  0000000140315A61: lea         rcx,[rbx+0000000000001BB0h]
  0000000140315A68: call        0000000140421100
  0000000140315A6D: lea         rcx,[rbx+0000000000001A78h]
  0000000140315A74: call        0000000140411200
  0000000140315A79: lea         rcx,[rbx+0000000000001940h]
  0000000140315A80: call        0000000140411200
  0000000140315A85: lea         rcx,[rbx+0000000000001808h]
  0000000140315A8C: call        0000000140411200
  0000000140315A91: lea         rcx,[rbx+00000000000016D0h]
  0000000140315A98: call        0000000140411200
  0000000140315A9D: 48
  0000000140315A9E: 8D
  0000000140315A9F: 8B
  0000000140315AA0: cwde

  Summary

      589000 .text
