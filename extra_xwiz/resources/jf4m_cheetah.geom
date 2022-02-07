; Used as data-layout template for conversion from VDS geom files.
; Geometry-relevant coordinates and parameters will be replaced.

adu_per_eV = 0.0042    ; 42 adu/keV for highest gain mode
clen =  0.101          ; to be replaced
photon_energy = 9460   ; to be replaced
res = 13333.3          ; 75 um pixels

data = /data/data
dim0 = %
dim1 = ss
dim2 = fs

rigid_group_p1 = p1a1,p1a2,p1a3,p1a4,p1a5,p1a6,p1a7,p1a8
rigid_group_p2 = p2a1,p2a2,p2a3,p2a4,p2a5,p2a6,p2a7,p2a8
rigid_group_p3 = p3a1,p3a2,p3a3,p3a4,p3a5,p3a6,p3a7,p3a8
rigid_group_p4 = p4a1,p4a2,p4a3,p4a4,p4a5,p4a6,p4a7,p4a8
rigid_group_p5 = p5a1,p5a2,p5a3,p5a4,p5a5,p5a6,p5a7,p5a8
rigid_group_p6 = p6a1,p6a2,p6a3,p6a4,p6a5,p6a6,p6a7,p6a8
rigid_group_p7 = p7a1,p7a2,p7a3,p7a4,p7a5,p7a6,p7a7,p7a8
rigid_group_p8 = p8a1,p8a2,p8a3,p8a4,p8a5,p8a6,p8a7,p8a8
;rigid_group_collection_asics = a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16
rigid_group_collection_det = p1,p2,p3,p4,p5,p6,p7,p8

p1a1/corner_x = 351.168
p1a1/corner_y = 811.908
p1a1/fs = -0.999973x +0.007381y
p1a1/ss = -0.007381x -0.999973y
p1a1/min_fs = 768
p1a1/max_fs = 1023
p1a1/min_ss = 256
p1a1/max_ss = 511

p1a2/corner_x = 609.161
p1a2/corner_y = 810.003
p1a2/fs = -0.999973x +0.007381y
p1a2/ss = -0.007381x -0.999973y
p1a2/min_fs = 512
p1a2/max_fs = 767
p1a2/min_ss = 256
p1a2/max_ss = 511

p1a3/corner_x = 867.154
p1a3/corner_y = 808.099
p1a3/fs = -0.999973x +0.007381y
p1a3/ss = -0.007381x -0.999973y
p1a3/min_fs = 256
p1a3/max_fs = 511
p1a3/min_ss = 256
p1a3/max_ss = 511

p1a4/corner_x = 1125.15
p1a4/corner_y = 806.195
p1a4/fs = -0.999973x +0.007381y
p1a4/ss = -0.007381x -0.999973y
p1a4/min_fs = 0
p1a4/max_fs = 255
p1a4/min_ss = 256
p1a4/max_ss = 511

p1a5/corner_x = 353.073
p1a5/corner_y = 1069.9
p1a5/fs = -0.999973x +0.007381y
p1a5/ss = -0.007381x -0.999973y
p1a5/min_fs = 768
p1a5/max_fs = 1023
p1a5/min_ss = 0
p1a5/max_ss = 255

p1a6/corner_x = 611.066
p1a6/corner_y = 1068
p1a6/fs = -0.999973x +0.007381y
p1a6/ss = -0.007381x -0.999973y
p1a6/min_fs = 512
p1a6/max_fs = 767
p1a6/min_ss = 0
p1a6/max_ss = 255

p1a7/corner_x = 869.059
p1a7/corner_y = 1066.09
p1a7/fs = -0.999973x +0.007381y
p1a7/ss = -0.007381x -0.999973y
p1a7/min_fs = 256
p1a7/max_fs = 511
p1a7/min_ss = 0
p1a7/max_ss = 255

p1a8/corner_x = 1127.05
p1a8/corner_y = 1064.19
p1a8/fs = -0.999973x +0.007381y
p1a8/ss = -0.007381x -0.999973y
p1a8/min_fs = 0
p1a8/max_fs = 255
p1a8/min_ss = 0
p1a8/max_ss = 255

p2a1/corner_x = 346.292
p2a1/corner_y = 263.531
p2a1/fs = -0.999994x +0.003611y
p2a1/ss = -0.003611x -0.999994y
p2a1/min_fs = 768
p2a1/max_fs = 1023
p2a1/min_ss = 768
p2a1/max_ss = 1023

p2a2/corner_x = 604.29
p2a2/corner_y = 262.599
p2a2/fs = -0.999994x +0.003611y
p2a2/ss = -0.003611x -0.999994y
p2a2/min_fs = 512
p2a2/max_fs = 767
p2a2/min_ss = 768
p2a2/max_ss = 1023

p2a3/corner_x = 862.289
p2a3/corner_y = 261.667
p2a3/fs = -0.999994x +0.003611y
p2a3/ss = -0.003611x -0.999994y
p2a3/min_fs = 256
p2a3/max_fs = 511
p2a3/min_ss = 768
p2a3/max_ss = 1023

p2a4/corner_x = 1120.28
p2a4/corner_y = 260.735
p2a4/fs = -0.999994x +0.003611y
p2a4/ss = -0.003611x -0.999994y
p2a4/min_fs = 0
p2a4/max_fs = 255
p2a4/min_ss = 768
p2a4/max_ss = 1023

p2a5/corner_x = 347.224
p2a5/corner_y = 521.529
p2a5/fs = -0.999994x +0.003611y
p2a5/ss = -0.003611x -0.999994y
p2a5/min_fs = 768
p2a5/max_fs = 1023
p2a5/min_ss = 512
p2a5/max_ss = 767

p2a6/corner_x = 605.222
p2a6/corner_y = 520.597
p2a6/fs = -0.999994x +0.003611y
p2a6/ss = -0.003611x -0.999994y
p2a6/min_fs = 512
p2a6/max_fs = 767
p2a6/min_ss = 512
p2a6/max_ss = 767

p2a7/corner_x = 863.22
p2a7/corner_y = 519.665
p2a7/fs = -0.999994x +0.003611y
p2a7/ss = -0.003611x -0.999994y
p2a7/min_fs = 256
p2a7/max_fs = 511
p2a7/min_ss = 512
p2a7/max_ss = 767

p2a8/corner_x = 1121.21
p2a8/corner_y = 518.733
p2a8/fs = -0.999994x +0.003611y
p2a8/ss = -0.003611x -0.999994y
p2a8/min_fs = 0
p2a8/max_fs = 255
p2a8/min_ss = 512
p2a8/max_ss = 767

p3a1/corner_x = 343.474
p3a1/corner_y = -284.249
p3a1/fs = -0.999998x +0.002283y
p3a1/ss = -0.002283x -0.999998y
p3a1/min_fs = 768
p3a1/max_fs = 1023
p3a1/min_ss = 1280
p3a1/max_ss = 1535

p3a2/corner_x = 601.473
p3a2/corner_y = -284.838
p3a2/fs = -0.999998x +0.002283y
p3a2/ss = -0.002283x -0.999998y
p3a2/min_fs = 512
p3a2/max_fs = 767
p3a2/min_ss = 1280
p3a2/max_ss = 1535

p3a3/corner_x = 859.472
p3a3/corner_y = -285.427
p3a3/fs = -0.999998x +0.002283y
p3a3/ss = -0.002283x -0.999998y
p3a3/min_fs = 256
p3a3/max_fs = 511
p3a3/min_ss = 1280
p3a3/max_ss = 1535

p3a4/corner_x = 1117.47
p3a4/corner_y = -286.016
p3a4/fs = -0.999998x +0.002283y
p3a4/ss = -0.002283x -0.999998y
p3a4/min_fs = 0
p3a4/max_fs = 255
p3a4/min_ss = 1280
p3a4/max_ss = 1535

p3a5/corner_x = 344.063
p3a5/corner_y = -26.2493
p3a5/fs = -0.999998x +0.002283y
p3a5/ss = -0.002283x -0.999998y
p3a5/min_fs = 768
p3a5/max_fs = 1023
p3a5/min_ss = 1024
p3a5/max_ss = 1279

p3a6/corner_x = 602.062
p3a6/corner_y = -26.8382
p3a6/fs = -0.999998x +0.002283y
p3a6/ss = -0.002283x -0.999998y
p3a6/min_fs = 512
p3a6/max_fs = 767
p3a6/min_ss = 1024
p3a6/max_ss = 1279

p3a7/corner_x = 860.061
p3a7/corner_y = -27.4271
p3a7/fs = -0.999998x +0.002283y
p3a7/ss = -0.002283x -0.999998y
p3a7/min_fs = 256
p3a7/max_fs = 511
p3a7/min_ss = 1024
p3a7/max_ss = 1279

p3a8/corner_x = 1118.06
p3a8/corner_y = -28.016
p3a8/fs = -0.999998x +0.002283y
p3a8/ss = -0.002283x -0.999998y
p3a8/min_fs = 0
p3a8/max_fs = 255
p3a8/min_ss = 1024
p3a8/max_ss = 1279


p4a1/corner_x = 343.474
p4a1/corner_y = -832.249
p4a1/fs = -0.999998x +0.002283y
p4a1/ss = -0.002283x -0.999998y
p4a1/min_fs = 768
p4a1/max_fs = 1023
p4a1/min_ss  =  1792
p4a1/max_ss  =  2047

p4a2/corner_x = 601.473
p4a2/corner_y = -832.838
p4a2/fs = -0.999998x +0.002283y
p4a2/ss = -0.002283x -0.999998y
p4a2/min_fs = 512
p4a2/max_fs = 767
p4a2/min_ss  =  1792
p4a2/max_ss  =  2047

p4a3/corner_x = 859.472
p4a3/corner_y = -833.427
p4a3/fs = -0.999998x +0.002283y
p4a3/ss = -0.002283x -0.999998y
p4a3/min_fs = 256
p4a3/max_fs = 511
p4a3/min_ss  =  1792
p4a3/max_ss  =  2047

p4a4/corner_x = 1117.47
p4a4/corner_y = -834.016
p4a4/fs = -0.999998x +0.002283y
p4a4/ss = -0.002283x -0.999998y
p4a4/min_fs = 0
p4a4/max_fs = 255
p4a4/min_ss  =  1792
p4a4/max_ss  =  2047

p4a5/corner_x = 344.063
p4a5/corner_y = -574.2493
p4a5/fs = -0.999998x +0.002283y
p4a5/ss = -0.002283x -0.999998y
p4a5/min_fs = 768
p4a5/max_fs = 1023
p4a5/min_ss  =  1536
p4a5/max_ss  =  1791

p4a6/corner_x = 602.062
p4a6/corner_y = -574.8382
p4a6/fs = -0.999998x +0.002283y
p4a6/ss = -0.002283x -0.999998y
p4a6/min_fs = 512
p4a6/max_fs = 767
p4a6/min_ss  =  1536
p4a6/max_ss  =  1791

p4a7/corner_x = 860.061
p4a7/corner_y = -575.4271
p4a7/fs = -0.999998x +0.002283y
p4a7/ss = -0.002283x -0.999998y
p4a7/min_fs = 256
p4a7/max_fs = 511
p4a7/min_ss  =  1536
p4a7/max_ss  =  1791

p4a8/corner_x = 1118.06
p4a8/corner_y = -576.016
p4a8/fs = -0.999998x +0.002283y
p4a8/ss = -0.002283x -0.999998y
p4a8/min_fs = 0
p4a8/max_fs = 255
p4a8/min_ss  =  1536
p4a8/max_ss  =  1791

p5a1/corner_x = -1133.24
p5a1/corner_y = -1085.736
p5a1/fs = +1.000000x +0.000194y
p5a1/ss = -0.000194x +1.000000y
p5a1/min_fs = 0
p5a1/max_fs = 255
p5a1/min_ss  =  2048
p5a1/max_ss  =  2303

p5a2/corner_x = -875.241
p5a2/corner_y = -1085.687
p5a2/fs = +1.000000x +0.000194y
p5a2/ss = -0.000194x +1.000000y
p5a2/min_fs = 256
p5a2/max_fs = 511
p5a2/min_ss  =  2048
p5a2/max_ss  =  2303

p5a3/corner_x = -617.241
p5a3/corner_y = -1085.637
p5a3/fs = +1.000000x +0.000194y
p5a3/ss = -0.000194x +1.000000y
p5a3/min_fs = 512
p5a3/max_fs = 767
p5a3/min_ss  =  2048
p5a3/max_ss  =  2303

p5a4/corner_x = -359.241
p5a4/corner_y = -1085.586
p5a4/fs = +1.000000x +0.000194y
p5a4/ss = -0.000194x +1.000000y
p5a4/min_fs = 768
p5a4/max_fs = 1023
p5a4/min_ss  =  2048
p5a4/max_ss  =  2303

p5a5/corner_x = -1133.3
p5a5/corner_y = -827.736
p5a5/fs = +1.000000x +0.000194y
p5a5/ss = -0.000194x +1.000000y
p5a5/min_fs = 0
p5a5/max_fs = 255
p5a5/min_ss  =  2304
p5a5/max_ss  =  2559

p5a6/corner_x = -875.291
p5a6/corner_y = -827.687
p5a6/fs = +1.000000x +0.000194y
p5a6/ss = -0.000194x +1.000000y
p5a6/min_fs = 256
p5a6/max_fs = 511
p5a6/min_ss  =  2304
p5a6/max_ss  =  2559

p5a7/corner_x = -617.291
p5a7/corner_y = -827.637
p5a7/fs = +1.000000x +0.000194y
p5a7/ss = -0.000194x +1.000000y
p5a7/min_fs = 512
p5a7/max_fs = 767
p5a7/min_ss  =  2304
p5a7/max_ss  =  2559

p5a8/corner_x = -359.291
p5a8/corner_y = -827.586
p5a8/fs = +1.000000x +0.000194y
p5a8/ss = -0.000194x +1.000000y
p5a8/min_fs = 768
p5a8/max_fs = 1023
p5a8/min_ss  =  2304
p5a8/max_ss  =  2559

p6a1/corner_x = -1133.24
p6a1/corner_y = -539.736
p6a1/fs = +1.000000x +0.000194y
p6a1/ss = -0.000194x +1.000000y
p6a1/min_fs = 0
p6a1/max_fs = 255
p6a1/min_ss  =  2560
p6a1/max_ss  =  2815

p6a2/corner_x = -875.241
p6a2/corner_y = -539.687
p6a2/fs = +1.000000x +0.000194y
p6a2/ss = -0.000194x +1.000000y
p6a2/min_fs = 256
p6a2/max_fs = 511
p6a2/min_ss  =  2560
p6a2/max_ss  =  2815

p6a3/corner_x = -617.241
p6a3/corner_y = -539.637
p6a3/fs = +1.000000x +0.000194y
p6a3/ss = -0.000194x +1.000000y
p6a3/min_fs = 512
p6a3/max_fs = 767
p6a3/min_ss  =  2560
p6a3/max_ss  =  2815

p6a4/corner_x = -359.241
p6a4/corner_y = -539.586
p6a4/fs = +1.000000x +0.000194y
p6a4/ss = -0.000194x +1.000000y
p6a4/min_fs = 768
p6a4/max_fs = 1023
p6a4/min_ss  =  2560
p6a4/max_ss  =  2815

p6a5/corner_x = -1133.3
p6a5/corner_y = -281.736
p6a5/fs = +1.000000x +0.000194y
p6a5/ss = -0.000194x +1.000000y
p6a5/min_fs = 0
p6a5/max_fs = 255
p6a5/min_ss  =  2816
p6a5/max_ss  =  3071

p6a6/corner_x = -875.291
p6a6/corner_y = -281.687
p6a6/fs = +1.000000x +0.000194y
p6a6/ss = -0.000194x +1.000000y
p6a6/min_fs = 256
p6a6/max_fs = 511
p6a6/min_ss  =  2816
p6a6/max_ss  =  3071

p6a7/corner_x = -617.291
p6a7/corner_y = -281.637
p6a7/fs = +1.000000x +0.000194y
p6a7/ss = -0.000194x +1.000000y
p6a7/min_fs = 512
p6a7/max_fs = 767
p6a7/min_ss  =  2816
p6a7/max_ss  =  3071

p6a8/corner_x = -359.291
p6a8/corner_y = -281.586
p6a8/fs = +1.000000x +0.000194y
p6a8/ss = -0.000194x +1.000000y
p6a8/min_fs = 768
p6a8/max_fs = 1023
p6a8/min_ss  =  2816
p6a8/max_ss  =  3071

p7a1/corner_x = -1130.27
p7a1/corner_y = 7.99532
p7a1/fs = +0.999994x +0.003298y
p7a1/ss = -0.003298x +0.999994y
p7a1/min_fs = 0
p7a1/max_fs = 255
p7a1/min_ss  =  3072
p7a1/max_ss  =  3327

p7a2/corner_x = -872.268
p7a2/corner_y = 8.84579
p7a2/fs = +0.999994x +0.003298y
p7a2/ss = -0.003298x +0.999994y
p7a2/min_fs = 256
p7a2/max_fs = 511
p7a2/min_ss  =  3072
p7a2/max_ss  =  3327

p7a3/corner_x = -614.269
p7a3/corner_y = 9.69625
p7a3/fs = +0.999994x +0.003298y
p7a3/ss = -0.003298x +0.999994y
p7a3/min_fs = 512
p7a3/max_fs = 767
p7a3/min_ss  =  3072
p7a3/max_ss  =  3327

p7a4/corner_x = -356.27
p7a4/corner_y = 10.5477
p7a4/fs = +0.999994x +0.003298y
p7a4/ss = -0.003298x +0.999994y
p7a4/min_fs = 768
p7a4/max_fs = 1023
p7a4/min_ss  =  3072
p7a4/max_ss  =  3327

p7a5/corner_x = -1131.11
p7a5/corner_y = 265.995
p7a5/fs = +0.999994x +0.003298y
p7a5/ss = -0.003298x +0.999994y
p7a5/min_fs = 0
p7a5/max_fs = 255
p7a5/min_ss  =  3328
p7a5/max_ss  =  3583

p7a6/corner_x = -873.118
p7a6/corner_y = 266.845
p7a6/fs = +0.999994x +0.003298y
p7a6/ss = -0.003298x +0.999994y
p7a6/min_fs = 256
p7a6/max_fs = 511
p7a6/min_ss  =  3328
p7a6/max_ss  =  3583

p7a7/corner_x = -615.119
p7a7/corner_y = 267.696
p7a7/fs = +0.999994x +0.003298y
p7a7/ss = -0.003298x +0.999994y
p7a7/min_fs = 512
p7a7/max_fs = 767
p7a7/min_ss  =  3328
p7a7/max_ss  =  3583

p7a8/corner_x = -357.121
p7a8/corner_y = 268.546
p7a8/fs = +0.999994x +0.003298y
p7a8/ss = -0.003298x +0.999994y
p7a8/min_fs = 768
p7a8/max_fs = 1023
p7a8/min_ss  =  3328
p7a8/max_ss  =  3583

p8a1/corner_x = -1130.62
p8a1/corner_y = 554.975
p8a1/fs = +0.999997x +0.002385y
p8a1/ss = -0.002385x +0.999997y
p8a1/min_fs = 0
p8a1/max_fs = 255
p8a1/min_ss  =  3584
p8a1/max_ss  =  3839
   
p8a2/corner_x = -872.609
p8a2/corner_y = 555.59
p8a2/fs = +0.999997x +0.002385y
p8a2/ss = -0.002385x +0.999997y
p8a2/min_fs = 256
p8a2/max_fs = 511
p8a2/min_ss  =  3584
p8a2/max_ss  =  3839

p8a3/corner_x = -614.609
p8a3/corner_y = 556.205
p8a3/fs = +0.999997x +0.002385y
p8a3/ss = -0.002385x +0.999997y
p8a3/min_fs = 512
p8a3/max_fs = 767
p8a3/min_ss  =  3584
p8a3/max_ss  =  3839

p8a4/corner_x = -356.61
p8a4/corner_y = 556.821
p8a4/fs = +0.999997x +0.002385y
p8a4/ss = -0.002385x +0.999997y
p8a4/min_fs = 768
p8a4/max_fs = 1023
p8a4/min_ss  =  3584
p8a4/max_ss  =  3839

p8a5/corner_x = -1131.23
p8a5/corner_y = 812.975
p8a5/fs = +0.999997x +0.002385y
p8a5/ss = -0.002385x +0.999997y
p8a5/min_fs = 0
p8a5/max_fs = 255
p8a5/min_ss  =  3840
p8a5/max_ss  =  4095

p8a6/corner_x = -873.224
p8a6/corner_y = 813.59
p8a6/fs = +0.999997x +0.002385y
p8a6/ss = -0.002385x +0.999997y
p8a6/min_fs = 256
p8a6/max_fs = 511
p8a6/min_ss  =  3840
p8a6/max_ss  =  4095

p8a7/corner_x = -615.224
p8a7/corner_y = 814.205
p8a7/fs = +0.999997x +0.002385y
p8a7/ss = -0.002385x +0.999997y
p8a7/min_fs = 512
p8a7/max_fs = 767
p8a7/min_ss  =  3840
p8a7/max_ss  =  4095

p8a8/corner_x = -357.225
p8a8/corner_y = 814.82
p8a8/fs = +0.999997x +0.002385y
p8a8/ss = -0.002385x +0.999997y
p8a8/min_fs = 768
p8a8/max_fs = 1023
p8a8/min_ss  =  3840
p8a8/max_ss  =  4095

p1a1/coffset = 0.000000
p1a2/coffset = 0.000000
p1a3/coffset = 0.000000
p1a4/coffset = 0.000000
p1a5/coffset = 0.000000
p1a6/coffset = 0.000000
p1a7/coffset = 0.000000
p1a8/coffset = 0.000000
p2a1/coffset = 0.000000
p2a2/coffset = 0.000000
p2a3/coffset = 0.000000
p2a4/coffset = 0.000000
p2a5/coffset = 0.000000
p2a6/coffset = 0.000000
p2a7/coffset = 0.000000
p2a8/coffset = 0.000000
p3a1/coffset = 0.000000
p3a2/coffset = 0.000000
p3a3/coffset = 0.000000
p3a4/coffset = 0.000000
p3a5/coffset = 0.000000
p3a6/coffset = 0.000000
p3a7/coffset = 0.000000
p3a8/coffset = 0.000000
p4a1/coffset = 0.000000
p4a2/coffset = 0.000000
p4a3/coffset = 0.000000
p4a4/coffset = 0.000000
p4a5/coffset = 0.000000
p4a6/coffset = 0.000000
p4a7/coffset = 0.000000
p4a8/coffset = 0.000000
p5a1/coffset = 0.000000
p5a2/coffset = 0.000000
p5a3/coffset = 0.000000
p5a4/coffset = 0.000000
p5a5/coffset = 0.000000
p5a6/coffset = 0.000000
p5a7/coffset = 0.000000
p5a8/coffset = 0.000000
p6a1/coffset = 0.000000
p6a2/coffset = 0.000000
p6a3/coffset = 0.000000
p6a4/coffset = 0.000000
p6a5/coffset = 0.000000
p6a6/coffset = 0.000000
p6a7/coffset = 0.000000
p6a8/coffset = 0.000000
p7a1/coffset = 0.000000
p7a2/coffset = 0.000000
p7a3/coffset = 0.000000
p7a4/coffset = 0.000000
p7a5/coffset = 0.000000
p7a6/coffset = 0.000000
p7a7/coffset = 0.000000
p7a8/coffset = 0.000000
p8a1/coffset = 0.000000
p8a2/coffset = 0.000000
p8a3/coffset = 0.000000
p8a4/coffset = 0.000000
p8a5/coffset = 0.000000
p8a6/coffset = 0.000000
p8a7/coffset = 0.000000
p8a8/coffset = 0.000000

