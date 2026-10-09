
SERIES{ 
    title = "IACA-BIOETANOL -  FLOW  -  LOG"
    file = "C:\mysyncfolders\BOLSA DE COMERCIO DE ROSARIO\IyEE Privado - DIYEE - IYEE (Privado)\IACA\IACA\BCR_AE\IACA-BIOETANOL.prn"
    period = 12
    span = (2010.01,)
    start = 2010.01
    modelspan = (2010.01,)
#
    appendbcst = YES
    appendfcst = YES
    decimals = 2
    format = free
}
TRANSFORM{ 
    function = LOG
    print = (TAC TRN)
    savelog = ATR
}
REGRESSION{ 
    aictest = (TD EASTER)
    savelog = AICTEST
}
AUTOMDL{ 
    maxdiff = (1 1)
    maxorder = (2 1)
    print = DEFAULT
    savelog = ALL
}
FORECAST{ 
    maxlead = 12
    maxback = 12
    print = (BCT FCT)  
    save = FCT
}
ESTIMATE{
    maxiter = 6000
    print = (DEFAULT RTS)  
    savelog = ALL
#    save = RSD
}
CHECK{ 
    maxlag = 36
    print = DEFAULT
    savelog = ALL
}
X11{
    appendbcst = NO
    appendfcst = YES
    seasonalma = MSR
    print = (BRIEF D9A D12 RSF)
    savelog = ALL
    save = (C17 D11 D12 D16)
#    save = (C17 D11 D12 D16 D13 D8)
}
SLIDINGSPANS{ 
    additivesa = percent
    savelog = PCT
    print = DEFAULT
}
SPECTRUM{ 
    savelog = ALL
    print = DEFAULT
}