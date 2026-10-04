Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  000000014031D8B0: mov         qword ptr [rsp+8],rbx
  000000014031D8B5: push        rdi
  000000014031D8B6: sub         rsp,20h
  000000014031D8BA: mov         rdi,rcx
  000000014031D8BD: xor         bl,bl
  000000014031D8BF: nop
  000000014031D8C0: mov         rax,qword ptr [rdi]
  000000014031D8C3: movzx       edx,bl
  000000014031D8C6: mov         rcx,rdi
  000000014031D8C9: call        qword ptr [rax+0000000000000138h]
  000000014031D8CF: mov         rax,qword ptr [rdi]
  000000014031D8D2: movzx       edx,bl
  000000014031D8D5: or          dl,10h
  000000014031D8D8: mov         rcx,rdi
  000000014031D8DB: call        qword ptr [rax+0000000000000138h]
  000000014031D8E1: inc         bl
  000000014031D8E3: cmp         bl,7
  000000014031D8E6: jb          000000014031D8C0
  000000014031D8E8: mov         rbx,qword ptr [rsp+30h]
  000000014031D8ED: add         rsp,20h
  000000014031D8F1: pop         rdi
  000000014031D8F2: ret
  000000014031D8F3: int         3
  000000014031D8F4: int         3
  000000014031D8F5: int         3
  000000014031D8F6: int         3
  000000014031D8F7: int         3
  000000014031D8F8: int         3
  000000014031D8F9: int         3
  000000014031D8FA: int         3
  000000014031D8FB: int         3
  000000014031D8FC: int         3
  000000014031D8FD: int         3
  000000014031D8FE: int         3
  000000014031D8FF: int         3
  000000014031D900: push        rbx
  000000014031D902: sub         rsp,20h
  000000014031D906: cmp         dword ptr [rcx+0000000000001738h],0
  000000014031D90D: mov         rbx,rcx
  000000014031D910: je          000000014031D957
  000000014031D912: mov         qword ptr [rsp+30h],rdi
  000000014031D917: xor         dil,dil
  000000014031D91A: nop         word ptr [rax+rax]
  000000014031D920: mov         rax,qword ptr [rbx]
  000000014031D923: movzx       edx,dil
  000000014031D927: mov         rcx,rbx
  000000014031D92A: call        qword ptr [rax+0000000000000138h]
  000000014031D930: mov         rax,qword ptr [rbx]
  000000014031D933: movzx       edx,dil
  000000014031D937: or          dl,10h
  000000014031D93A: mov         rcx,rbx
  000000014031D93D: call        qword ptr [rax+0000000000000138h]
  000000014031D943: inc         dil
  000000014031D946: cmp         dil,7
  000000014031D94A: jb          000000014031D920
  000000014031D94C: mov         rdi,qword ptr [rsp+30h]
  000000014031D951: add         rsp,20h
  000000014031D955: pop         rbx
  000000014031D956: ret
  000000014031D957: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031D95E: mov         edx,ecx
  000000014031D960: mov         eax,ecx
  000000014031D962: shl         edx,8
  000000014031D965: shl         eax,10h
  000000014031D968: or          edx,eax
  000000014031D96A: or          edx,ecx
  000000014031D96C: lea         rcx,[rbx+0000000000000CF8h]
  000000014031D973: call        0000000140412690
  000000014031D978: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031D97F: mov         edx,ecx
  000000014031D981: mov         eax,ecx
  000000014031D983: shl         edx,8
  000000014031D986: shl         eax,10h
  000000014031D989: or          edx,eax
  000000014031D98B: or          edx,ecx
  000000014031D98D: lea         rcx,[rbx+0000000000000F68h]
  000000014031D994: call        0000000140412690
  000000014031D999: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031D9A0: mov         edx,ecx
  000000014031D9A2: mov         eax,ecx
  000000014031D9A4: shl         edx,8
  000000014031D9A7: shl         eax,10h
  000000014031D9AA: or          edx,eax
  000000014031D9AC: or          edx,ecx
  000000014031D9AE: lea         rcx,[rbx+0000000000001220h]
  000000014031D9B5: call        0000000140412690
  000000014031D9BA: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031D9C1: mov         edx,ecx
  000000014031D9C3: mov         eax,ecx
  000000014031D9C5: shl         edx,8
  000000014031D9C8: shl         eax,10h
  000000014031D9CB: or          edx,eax
  000000014031D9CD: or          edx,ecx
  000000014031D9CF: lea         rcx,[rbx+0000000000001490h]
  000000014031D9D6: call        0000000140412690
  000000014031D9DB: cmp         dword ptr [000000014070FD18h],0
  000000014031D9E2: jne         000000014031DA6C
  000000014031D9E8: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031D9EF: mov         edx,ecx
  000000014031D9F1: mov         eax,ecx
  000000014031D9F3: shl         edx,8
  000000014031D9F6: shl         eax,10h
  000000014031D9F9: or          edx,eax
  000000014031D9FB: or          edx,ecx
  000000014031D9FD: lea         rcx,[rbx+0000000000000E30h]
  000000014031DA04: call        0000000140412690
  000000014031DA09: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DA10: mov         edx,ecx
  000000014031DA12: mov         eax,ecx
  000000014031DA14: shl         edx,8
  000000014031DA17: shl         eax,10h
  000000014031DA1A: or          edx,eax
  000000014031DA1C: or          edx,ecx
  000000014031DA1E: lea         rcx,[rbx+00000000000010A0h]
  000000014031DA25: call        0000000140412690
  000000014031DA2A: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DA31: mov         edx,ecx
  000000014031DA33: mov         eax,ecx
  000000014031DA35: shl         edx,8
  000000014031DA38: shl         eax,10h
  000000014031DA3B: or          edx,eax
  000000014031DA3D: or          edx,ecx
  000000014031DA3F: lea         rcx,[rbx+0000000000001358h]
  000000014031DA46: call        0000000140412690
  000000014031DA4B: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DA52: mov         edx,ecx
  000000014031DA54: mov         eax,ecx
  000000014031DA56: shl         edx,8
  000000014031DA59: shl         eax,10h
  000000014031DA5C: or          edx,eax
  000000014031DA5E: or          edx,ecx
  000000014031DA60: lea         rcx,[rbx+00000000000015C8h]
  000000014031DA67: call        0000000140412690
  000000014031DA6C: lea         rcx,[rbx+0000000000000CF0h]
  000000014031DA73: call        0000000140411570
  000000014031DA78: lea         rcx,[rbx+0000000000000F60h]
  000000014031DA7F: call        0000000140411570
  000000014031DA84: lea         rcx,[rbx+0000000000001218h]
  000000014031DA8B: mov         byte ptr [rbx+0000000000000DF7h],0
  000000014031DA92: mov         byte ptr [rbx+0000000000001067h],0
  000000014031DA99: call        0000000140411570
  000000014031DA9E: lea         rcx,[rbx+0000000000001488h]
  000000014031DAA5: call        0000000140411570
  000000014031DAAA: mov         byte ptr [rbx+000000000000131Fh],0
  000000014031DAB1: mov         byte ptr [rbx+000000000000158Fh],0
  000000014031DAB8: cmp         dword ptr [000000014070FD18h],0
  000000014031DABF: jne         000000014031DAE7
  000000014031DAC1: lea         rcx,[rbx+0000000000001350h]
  000000014031DAC8: call        0000000140411570
  000000014031DACD: lea         rcx,[rbx+00000000000015C0h]
  000000014031DAD4: call        0000000140411570
  000000014031DAD9: mov         byte ptr [rbx+0000000000001457h],0
  000000014031DAE0: mov         byte ptr [rbx+00000000000016C7h],0
  000000014031DAE7: add         rsp,20h
  000000014031DAEB: pop         rbx
  000000014031DAEC: ret
  000000014031DAED: int         3
  000000014031DAEE: int         3
  000000014031DAEF: int         3
  000000014031DAF0: mov         qword ptr [rsp+10h],rbx
  000000014031DAF5: push        rdi
  000000014031DAF6: sub         rsp,20h
  000000014031DAFA: cmp         dword ptr [rcx+0000000000000D50h],0
  000000014031DB01: mov         rdi,rcx
  000000014031DB04: je          000000014031DB31
  000000014031DB06: xor         bl,bl
  000000014031DB08: nop         dword ptr [rax+rax+0000000000000000h]
  000000014031DB10: mov         rax,qword ptr [rdi]
  000000014031DB13: movzx       edx,bl
  000000014031DB16: mov         rcx,rdi
  000000014031DB19: call        qword ptr [rax+0000000000000138h]
  000000014031DB1F: inc         bl
  000000014031DB21: cmp         bl,7
  000000014031DB24: jb          000000014031DB10
  000000014031DB26: mov         rbx,qword ptr [rsp+38h]
  000000014031DB2B: add         rsp,20h
  000000014031DB2F: pop         rdi
  000000014031DB30: ret
  000000014031DB31: mov         qword ptr [rsp+30h],rsi
  000000014031DB36: xor         sil,sil
  000000014031DB39: cmp         byte ptr [rcx+00000000000012F9h],sil
  000000014031DB40: jbe         000000014031DCC9
  000000014031DB46: nop         word ptr [rax+rax+0000000000000000h]
  000000014031DB50: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DB57: mov         edx,ecx
  000000014031DB59: movzx       eax,sil
  000000014031DB5D: imul        rbx,rax,138h
  000000014031DB64: mov         eax,ecx
  000000014031DB66: shl         edx,8
  000000014031DB69: shl         eax,10h
  000000014031DB6C: or          edx,eax
  000000014031DB6E: or          edx,ecx
  000000014031DB70: mov         rcx,qword ptr [rdi+0000000000000CE8h]
  000000014031DB77: add         rcx,8
  000000014031DB7B: add         rcx,rbx
  000000014031DB7E: call        0000000140412690
  000000014031DB83: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DB8A: mov         edx,ecx
  000000014031DB8C: mov         eax,ecx
  000000014031DB8E: shl         edx,8
  000000014031DB91: shl         eax,10h
  000000014031DB94: or          edx,eax
  000000014031DB96: or          edx,ecx
  000000014031DB98: mov         rcx,qword ptr [rdi+0000000000000CF0h]
  000000014031DB9F: add         rcx,8
  000000014031DBA3: add         rcx,rbx
  000000014031DBA6: call        0000000140412690
  000000014031DBAB: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DBB2: mov         edx,ecx
  000000014031DBB4: mov         eax,ecx
  000000014031DBB6: shl         edx,8
  000000014031DBB9: shl         eax,10h
  000000014031DBBC: or          edx,eax
  000000014031DBBE: or          edx,ecx
  000000014031DBC0: mov         rcx,qword ptr [rdi+0000000000000CF8h]
  000000014031DBC7: add         rcx,8
  000000014031DBCB: add         rcx,rbx
  000000014031DBCE: call        0000000140412690
  000000014031DBD3: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DBDA: mov         edx,ecx
  000000014031DBDC: mov         eax,ecx
  000000014031DBDE: shl         edx,8
  000000014031DBE1: shl         eax,10h
  000000014031DBE4: or          edx,eax
  000000014031DBE6: or          edx,ecx
  000000014031DBE8: mov         rcx,qword ptr [rdi+0000000000000D00h]
  000000014031DBEF: add         rcx,8
  000000014031DBF3: add         rcx,rbx
  000000014031DBF6: call        0000000140412690
  000000014031DBFB: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DC02: mov         edx,ecx
  000000014031DC04: mov         eax,ecx
  000000014031DC06: shl         edx,8
  000000014031DC09: shl         eax,10h
  000000014031DC0C: or          edx,eax
  000000014031DC0E: or          edx,ecx
  000000014031DC10: mov         rcx,qword ptr [rdi+0000000000000D08h]
  000000014031DC17: add         rcx,8
  000000014031DC1B: add         rcx,rbx
  000000014031DC1E: call        0000000140412690
  000000014031DC23: mov         rcx,qword ptr [rdi+0000000000000CE8h]
  000000014031DC2A: add         rcx,rbx
  000000014031DC2D: call        0000000140411570
  000000014031DC32: mov         rcx,qword ptr [rdi+0000000000000CF0h]
  000000014031DC39: add         rcx,rbx
  000000014031DC3C: call        0000000140411570
  000000014031DC41: mov         rcx,qword ptr [rdi+0000000000000CF8h]
  000000014031DC48: add         rcx,rbx
  000000014031DC4B: call        0000000140411570
  000000014031DC50: mov         rcx,qword ptr [rdi+0000000000000D00h]
  000000014031DC57: add         rcx,rbx
  000000014031DC5A: call        0000000140411570
  000000014031DC5F: mov         rcx,qword ptr [rdi+0000000000000D08h]
  000000014031DC66: add         rcx,rbx
  000000014031DC69: call        0000000140411570
  000000014031DC6E: mov         rax,qword ptr [rdi+0000000000000CE8h]
  000000014031DC75: mov         byte ptr [rax+rbx+0000000000000107h],0
  000000014031DC7D: mov         rax,qword ptr [rdi+0000000000000CF0h]
  000000014031DC84: mov         byte ptr [rax+rbx+0000000000000107h],0
  000000014031DC8C: mov         rax,qword ptr [rdi+0000000000000CF8h]
  000000014031DC93: mov         byte ptr [rax+rbx+0000000000000107h],0
  000000014031DC9B: mov         rax,qword ptr [rdi+0000000000000D00h]
  000000014031DCA2: mov         byte ptr [rax+rbx+0000000000000107h],0
  000000014031DCAA: mov         rax,qword ptr [rdi+0000000000000D08h]
  000000014031DCB1: inc         sil
  000000014031DCB4: mov         byte ptr [rax+rbx+0000000000000107h],0
  000000014031DCBC: cmp         sil,byte ptr [rdi+00000000000012F9h]
  000000014031DCC3: jb          000000014031DB50
  000000014031DCC9: mov         rsi,qword ptr [rsp+30h]
  000000014031DCCE: mov         rbx,qword ptr [rsp+38h]
  000000014031DCD3: add         rsp,20h
  000000014031DCD7: pop         rdi
  000000014031DCD8: ret
  000000014031DCD9: int         3
  000000014031DCDA: int         3
  000000014031DCDB: int         3
  000000014031DCDC: int         3
  000000014031DCDD: int         3
  000000014031DCDE: int         3
  000000014031DCDF: int         3
  000000014031DCE0: mov         qword ptr [rsp+18h],rbx
  000000014031DCE5: push        rdi
  000000014031DCE6: sub         rsp,20h
  000000014031DCEA: cmp         dword ptr [rcx+0000000000000D30h],0
  000000014031DCF1: mov         rbx,rcx
  000000014031DCF4: je          000000014031DD37
  000000014031DCF6: xor         dil,dil
  000000014031DCF9: nop         dword ptr [rax+0000000000000000h]
  000000014031DD00: mov         rax,qword ptr [rbx]
  000000014031DD03: movzx       edx,dil
  000000014031DD07: mov         rcx,rbx
  000000014031DD0A: call        qword ptr [rax+0000000000000138h]
  000000014031DD10: mov         rax,qword ptr [rbx]
  000000014031DD13: movzx       edx,dil
  000000014031DD17: or          dl,10h
  000000014031DD1A: mov         rcx,rbx
  000000014031DD1D: call        qword ptr [rax+0000000000000138h]
  000000014031DD23: inc         dil
  000000014031DD26: cmp         dil,7
  000000014031DD2A: jb          000000014031DD00
  000000014031DD2C: mov         rbx,qword ptr [rsp+40h]
  000000014031DD31: add         rsp,20h
  000000014031DD35: pop         rdi
  000000014031DD36: ret
  000000014031DD37: mov         qword ptr [rsp+38h],rsi
  000000014031DD3C: xor         esi,esi
  000000014031DD3E: cmp         byte ptr [rcx+0000000000000D35h],sil
  000000014031DD45: jbe         000000014031DDFF
  000000014031DD4B: mov         qword ptr [rsp+30h],rbp
  000000014031DD50: mov         ebp,esi
  000000014031DD52: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DD59: mov         edx,ecx
  000000014031DD5B: movsxd      rax,esi
  000000014031DD5E: imul        rdi,rax,138h
  000000014031DD65: mov         eax,ecx
  000000014031DD67: shl         edx,8
  000000014031DD6A: shl         eax,10h
  000000014031DD6D: or          edx,eax
  000000014031DD6F: or          edx,ecx
  000000014031DD71: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  000000014031DD78: add         rcx,8
  000000014031DD7C: add         rcx,rdi
  000000014031DD7F: call        0000000140412690
  000000014031DD84: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DD8B: mov         edx,ecx
  000000014031DD8D: mov         eax,ecx
  000000014031DD8F: shl         edx,8
  000000014031DD92: shl         eax,10h
  000000014031DD95: or          edx,eax
  000000014031DD97: or          edx,ecx
  000000014031DD99: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  000000014031DDA0: add         rcx,8
  000000014031DDA4: add         rcx,rdi
  000000014031DDA7: call        0000000140412690
  000000014031DDAC: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  000000014031DDB3: add         rcx,rdi
  000000014031DDB6: call        0000000140411570
  000000014031DDBB: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  000000014031DDC2: add         rcx,rdi
  000000014031DDC5: call        0000000140411570
  000000014031DDCA: mov         rax,qword ptr [rbx+0000000000000CE8h]
  000000014031DDD1: lea         rbp,[rbp+0000000000000138h]
  000000014031DDD8: inc         esi
  000000014031DDDA: mov         byte ptr [rax+rbp-31h],0
  000000014031DDDF: mov         rax,qword ptr [rbx+0000000000000CF0h]
  000000014031DDE6: mov         byte ptr [rax+rbp-31h],0
  000000014031DDEB: movzx       eax,byte ptr [rbx+0000000000000D35h]
  000000014031DDF2: cmp         esi,eax
  000000014031DDF4: jl          000000014031DD52
  000000014031DDFA: mov         rbp,qword ptr [rsp+30h]
  000000014031DDFF: mov         rsi,qword ptr [rsp+38h]
  000000014031DE04: mov         rbx,qword ptr [rsp+40h]
  000000014031DE09: add         rsp,20h
  000000014031DE0D: pop         rdi
  000000014031DE0E: ret
  000000014031DE0F: int         3
  000000014031DE10: push        rbx
  000000014031DE12: sub         rsp,20h
  000000014031DE16: cmp         dword ptr [rcx+0000000000001204h],0
  000000014031DE1D: mov         rbx,rcx
  000000014031DE20: je          000000014031DE54
  000000014031DE22: mov         qword ptr [rsp+30h],rdi
  000000014031DE27: xor         dil,dil
  000000014031DE2A: nop         word ptr [rax+rax]
  000000014031DE30: mov         rax,qword ptr [rbx]
  000000014031DE33: movzx       edx,dil
  000000014031DE37: mov         rcx,rbx
  000000014031DE3A: call        qword ptr [rax+0000000000000138h]
  000000014031DE40: inc         dil
  000000014031DE43: cmp         dil,7
  000000014031DE47: jb          000000014031DE30
  000000014031DE49: mov         rdi,qword ptr [rsp+30h]
  000000014031DE4E: add         rsp,20h
  000000014031DE52: pop         rbx
  000000014031DE53: ret
  000000014031DE54: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DE5B: mov         edx,ecx
  000000014031DE5D: mov         eax,ecx
  000000014031DE5F: shl         edx,8
  000000014031DE62: shl         eax,10h
  000000014031DE65: or          edx,eax
  000000014031DE67: or          edx,ecx
  000000014031DE69: lea         rcx,[rbx+0000000000000CF8h]
  000000014031DE70: call        0000000140412690
  000000014031DE75: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DE7C: mov         edx,ecx
  000000014031DE7E: mov         eax,ecx
  000000014031DE80: shl         edx,8
  000000014031DE83: shl         eax,10h
  000000014031DE86: or          edx,eax
  000000014031DE88: or          edx,ecx
  000000014031DE8A: lea         rcx,[rbx+0000000000000F68h]
  000000014031DE91: call        0000000140412690
  000000014031DE96: cmp         dword ptr [000000014070FD18h],0
  000000014031DE9D: jne         000000014031DEE1
  000000014031DE9F: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DEA6: mov         edx,ecx
  000000014031DEA8: mov         eax,ecx
  000000014031DEAA: shl         edx,8
  000000014031DEAD: shl         eax,10h
  000000014031DEB0: or          edx,eax
  000000014031DEB2: or          edx,ecx
  000000014031DEB4: lea         rcx,[rbx+0000000000000E30h]
  000000014031DEBB: call        0000000140412690
  000000014031DEC0: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DEC7: mov         edx,ecx
  000000014031DEC9: mov         eax,ecx
  000000014031DECB: shl         edx,8
  000000014031DECE: shl         eax,10h
  000000014031DED1: or          edx,eax
  000000014031DED3: or          edx,ecx
  000000014031DED5: lea         rcx,[rbx+00000000000010A0h]
  000000014031DEDC: call        0000000140412690
  000000014031DEE1: lea         rcx,[rbx+0000000000000CF0h]
  000000014031DEE8: call        0000000140411570
  000000014031DEED: lea         rcx,[rbx+0000000000000F60h]
  000000014031DEF4: call        0000000140411570
  000000014031DEF9: mov         byte ptr [rbx+0000000000000DF7h],0
  000000014031DF00: mov         byte ptr [rbx+0000000000001067h],0
  000000014031DF07: cmp         dword ptr [000000014070FD18h],0
  000000014031DF0E: jne         000000014031DF36
  000000014031DF10: lea         rcx,[rbx+0000000000000E28h]
  000000014031DF17: call        0000000140411570
  000000014031DF1C: lea         rcx,[rbx+0000000000001098h]
  000000014031DF23: call        0000000140411570
  000000014031DF28: mov         byte ptr [rbx+0000000000000F2Fh],0
  000000014031DF2F: mov         byte ptr [rbx+000000000000119Fh],0
  000000014031DF36: add         rsp,20h
  000000014031DF3A: pop         rbx
  000000014031DF3B: ret
  000000014031DF3C: int         3
  000000014031DF3D: int         3
  000000014031DF3E: int         3
  000000014031DF3F: int         3
  000000014031DF40: mov         qword ptr [rsp+10h],rbx
  000000014031DF45: push        rdi
  000000014031DF46: sub         rsp,20h
  000000014031DF4A: xor         dil,dil
  000000014031DF4D: mov         rbx,rcx
  000000014031DF50: cmp         dword ptr [rcx+0000000000000D54h],0
  000000014031DF57: je          000000014031DF84
  000000014031DF59: nop         dword ptr [rax+0000000000000000h]
  000000014031DF60: mov         rax,qword ptr [rbx]
  000000014031DF63: movzx       edx,dil
  000000014031DF67: mov         rcx,rbx
  000000014031DF6A: call        qword ptr [rax+0000000000000138h]
  000000014031DF70: inc         dil
  000000014031DF73: cmp         dil,7
  000000014031DF77: jb          000000014031DF60
  000000014031DF79: mov         rbx,qword ptr [rsp+38h]
  000000014031DF7E: add         rsp,20h
  000000014031DF82: pop         rdi
  000000014031DF83: ret
  000000014031DF84: cmp         byte ptr [rcx+0000000000000D59h],dil
  000000014031DF8B: jbe         000000014031E17E
  000000014031DF91: mov         qword ptr [rsp+30h],rsi
  000000014031DF96: nop         word ptr [rax+rax+0000000000000000h]
  000000014031DFA0: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DFA7: mov         edx,ecx
  000000014031DFA9: movzx       eax,dil
  000000014031DFAD: imul        rsi,rax,138h
  000000014031DFB4: mov         eax,ecx
  000000014031DFB6: shl         edx,8
  000000014031DFB9: shl         eax,10h
  000000014031DFBC: or          edx,eax
  000000014031DFBE: or          edx,ecx
  000000014031DFC0: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  000000014031DFC7: add         rcx,8
  000000014031DFCB: add         rcx,rsi
  000000014031DFCE: call        0000000140412690
  000000014031DFD3: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031DFDA: mov         edx,ecx
  000000014031DFDC: mov         eax,ecx
  000000014031DFDE: shl         edx,8
  000000014031DFE1: shl         eax,10h
  000000014031DFE4: or          edx,eax
  000000014031DFE6: or          edx,ecx
  000000014031DFE8: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  000000014031DFEF: add         rcx,8
  000000014031DFF3: add         rcx,rsi
  000000014031DFF6: call        0000000140412690
  000000014031DFFB: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031E002: mov         edx,ecx
  000000014031E004: mov         eax,ecx
  000000014031E006: shl         edx,8
  000000014031E009: shl         eax,10h
  000000014031E00C: or          edx,eax
  000000014031E00E: or          edx,ecx
  000000014031E010: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  000000014031E017: add         rcx,8
  000000014031E01B: add         rcx,rsi
  000000014031E01E: call        0000000140412690
  000000014031E023: mov         rcx,qword ptr [rbx+0000000000000CE8h]
  000000014031E02A: add         rcx,rsi
  000000014031E02D: call        0000000140411570
  000000014031E032: mov         rcx,qword ptr [rbx+0000000000000CF0h]
  000000014031E039: add         rcx,rsi
  000000014031E03C: call        0000000140411570
  000000014031E041: mov         rcx,qword ptr [rbx+0000000000000CF8h]
  000000014031E048: add         rcx,rsi
  000000014031E04B: call        0000000140411570
  000000014031E050: mov         rax,qword ptr [rbx+0000000000000CE8h]
  000000014031E057: mov         byte ptr [rax+rsi+0000000000000107h],0
  000000014031E05F: mov         rax,qword ptr [rbx+0000000000000CF0h]
  000000014031E066: mov         byte ptr [rax+rsi+0000000000000107h],0
  000000014031E06E: mov         rax,qword ptr [rbx+0000000000000CF8h]
  000000014031E075: mov         byte ptr [rax+rsi+0000000000000107h],0
  000000014031E07D: cmp         dword ptr [rbx+0000000000000D60h],0
  000000014031E084: je          000000014031E169
  000000014031E08A: cmp         dword ptr [000000014070FD18h],0
  000000014031E091: jne         000000014031E169
  000000014031E097: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031E09E: mov         edx,ecx
  000000014031E0A0: mov         eax,ecx
  000000014031E0A2: shl         edx,8
  000000014031E0A5: shl         eax,10h
  000000014031E0A8: or          edx,eax
  000000014031E0AA: or          edx,ecx
  000000014031E0AC: mov         rcx,qword ptr [rbx+0000000000000D08h]
  000000014031E0B3: add         rcx,8
  000000014031E0B7: add         rcx,rsi
  000000014031E0BA: call        0000000140412690
  000000014031E0BF: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031E0C6: mov         edx,ecx
  000000014031E0C8: mov         eax,ecx
  000000014031E0CA: shl         edx,8
  000000014031E0CD: shl         eax,10h
  000000014031E0D0: or          edx,eax
  000000014031E0D2: or          edx,ecx
  000000014031E0D4: mov         rcx,qword ptr [rbx+0000000000000D10h]
  000000014031E0DB: add         rcx,8
  000000014031E0DF: add         rcx,rsi
  000000014031E0E2: call        0000000140412690
  000000014031E0E7: movzx       ecx,byte ptr [00000001405C067Fh]
  000000014031E0EE: mov         edx,ecx
  000000014031E0F0: mov         eax,ecx
  000000014031E0F2: shl         edx,8
  000000014031E0F5: shl         eax,10h
  000000014031E0F8: or          edx,eax
  000000014031E0FA: or          edx,ecx
  000000014031E0FC: mov         rcx,qword ptr [rbx+0000000000000D18h]
  000000014031E103: add         rcx,8
  000000014031E107: add         rcx,rsi
  000000014031E10A: call        0000000140412690
  000000014031E10F: mov         rcx,qword ptr [rbx+0000000000000D08h]
  000000014031E116: add         rcx,rsi
  000000014031E119: call        0000000140411570
  000000014031E11E: mov         rcx,qword ptr [rbx+0000000000000D10h]
  000000014031E125: add         rcx,rsi
  000000014031E128: call        0000000140411570
  000000014031E12D: mov         rcx,qword ptr [rbx+0000000000000D18h]
  000000014031E134: add         rcx,rsi
  000000014031E137: call        0000000140411570
  000000014031E13C: mov         rax,qword ptr [rbx+0000000000000D08h]
  000000014031E143: mov         byte ptr [rsi+rax+0000000000000107h],0
  000000014031E14B: mov         rax,qword ptr [rbx+0000000000000D10h]
  000000014031E152: mov         byte ptr [rsi+rax+0000000000000107h],0
  000000014031E15A: mov         rax,qword ptr [rbx+0000000000000D18h]
  000000014031E161: mov         byte ptr [rsi+rax+0000000000000107h],0
  000000014031E169: inc         dil
  000000014031E16C: cmp         dil,byte ptr [rbx+0000000000000D59h]
  000000014031E173: jb          000000014031DFA0
  000000014031E179: mov         rsi,qword ptr [rsp+30h]
  000000014031E17E: mov         rbx,qword ptr [rsp+38h]
  000000014031E183: add         rsp,20h
  000000014031E187: pop         rdi
  000000014031E188: ret
  000000014031E189: int         3
  000000014031E18A: int         3
  000000014031E18B: int         3
  000000014031E18C: int         3
  000000014031E18D: int         3
  000000014031E18E: int         3
  000000014031E18F: int         3
  000000014031E190: mov         rax,qword ptr [rcx+0000000000000CD8h]
  000000014031E197: dec         word ptr [rax+0000000000000118h]
  000000014031E19E: ret
  000000014031E19F: int         3
  000000014031E1A0: mov         rax,qword ptr [rcx+0000000000000CD0h]
  000000014031E1A7: dec         word ptr [rax+0000000000000118h]
  000000014031E1AE: ret
  000000014031E1AF: int         3
  000000014031E1B0: mov         rax,qword ptr [rcx+0000000000000D00h]
  000000014031E1B7: dec         word ptr [rax+0000000000000118h]
  000000014031E1BE: mov         rax,qword ptr [rcx+0000000000001360h]
  000000014031E1C5: test        rax,rax
  000000014031E1C8: je          000000014031E1D1
  000000014031E1CA: dec         word ptr [rax+0000000000000118h]
  000000014031E1D1: mov         rax,qword ptr [rcx+0000000000001888h]
  000000014031E1D8: test        rax,rax
  000000014031E1DB: je          000000014031E1E4
  000000014031E1DD: dec         word ptr [rax+0000000000000118h]
  000000014031E1E4: mov         rax,qword ptr [rcx+0000000000001DB0h]
  000000014031E1EB: test        rax,rax
  000000014031E1EE: je          000000014031E1F7
  000000014031E1F0: dec         word ptr [rax+0000000000000118h]
  000000014031E1F7: ret
  000000014031E1F8: int         3
  000000014031E1F9: int         3
  000000014031E1FA: int         3
  000000014031E1FB: int         3
  000000014031E1FC: int         3
  000000014031E1FD: int         3
  000000014031E1FE: int         3
  000000014031E1FF: int         3
  000000014031E200: mov         rax,qword ptr [rcx+0000000000000CF8h]
  000000014031E207: dec         word ptr [rax+0000000000000118h]
  000000014031E20E: mov         rax,qword ptr [rcx+00000000000043D0h]
  000000014031E215: dec         word ptr [rax+0000000000000118h]
  000000014031E21C: mov         rax,qword ptr [rcx+0000000000001BE8h]
  000000014031E223: test        rax,rax
  000000014031E226: je          000000014031E22F
  000000014031E228: dec         word ptr [rax+0000000000000118h]
  000000014031E22F: mov         rax,qword ptr [rcx+0000000000002868h]
  000000014031E236: test        rax,rax
  000000014031E239: je          000000014031E242
  000000014031E23B: dec         word ptr [rax+0000000000000118h]
  000000014031E242: mov         rax,qword ptr [rcx+00000000000034E8h]
  000000014031E249: test        rax,rax
  000000014031E24C: je          000000014031E255
  000000014031E24E: dec         word ptr [rax+0000000000000118h]
  000000014031E255: ret
  000000014031E256: int         3
  000000014031E257: int         3
  000000014031E258: int         3
  000000014031E259: int         3
  000000014031E25A: int         3
  000000014031E25B: int         3
  000000014031E25C: int         3
  000000014031E25D: int         3
  000000014031E25E: int         3
  000000014031E25F: int         3
  000000014031E260: mov         rax,qword ptr [rcx+0000000000000CD8h]
  000000014031E267: dec         word ptr [rax+0000000000000118h]
  000000014031E26E: cmp         dword ptr [rcx+000000000000127Ch],0
  000000014031E275: je          000000014031E285
  000000014031E277: mov         rax,qword ptr [rcx+0000000000001288h]
  000000014031E27E: dec         word ptr [rax+0000000000000118h]
  000000014031E285: mov         rax,qword ptr [rcx+0000000000000F88h]
  000000014031E28C: test        rax,rax
  000000014031E28F: je          000000014031E298
  000000014031E291: dec         word ptr [rax+0000000000000118h]
  000000014031E298: ret
  000000014031E299: int         3
  000000014031E29A: int         3
  000000014031E29B: int         3
  000000014031E29C: int         3
  000000014031E29D: int         3
  000000014031E29E: int         3
  000000014031E29F: int         3
  000000014031E2A0: mov         rax,qword ptr [rcx+0000000000000CD8h]
  000000014031E2A7: dec         word ptr [rax+0000000000000118h]
  000000014031E2AE: mov         rax,qword ptr [rcx+0000000000001440h]
  000000014031E2B5: dec         word ptr [rax+0000000000000118h]
  000000014031E2BC: ret
  000000014031E2BD: int         3
  000000014031E2BE: int         3
  000000014031E2BF: int         3
  000000014031E2C0: mov         rax,qword ptr [rcx+0000000000000CD8h]
  000000014031E2C7: dec         word ptr [rax+0000000000000118h]
  000000014031E2CE: mov         rax,qword ptr [rcx+0000000000002F10h]
  000000014031E2D5: test        rax,rax
  000000014031E2D8: je          000000014031E2E1
  000000014031E2DA: dec         word ptr [rax+0000000000000118h]
  000000014031E2E1: ret
  000000014031E2E2: int         3
  000000014031E2E3: int         3
  000000014031E2E4: int         3
  000000014031E2E5: int         3
  000000014031E2E6: int         3
  000000014031E2E7: int         3
  000000014031E2E8: int         3
  000000014031E2E9: int         3
  000000014031E2EA: int         3
  000000014031E2EB: int         3
  000000014031E2EC: int         3
  000000014031E2ED: int         3
  000000014031E2EE: int         3
  000000014031E2EF: int         3
  000000014031E2F0: 48

  Summary

      589000 .text
