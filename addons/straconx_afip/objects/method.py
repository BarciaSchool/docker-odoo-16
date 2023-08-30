def check_only_number(cadena):
    try:
        if not cadena:
            return True
        if len(cadena)==3:
            if int(cadena[0])>=0:
                if int(cadena[1])>=0:
                    if int(cadena[2])>=1: 
                        return True
    except:
        return False

def check_only_authorization(cadena):
    try:
        if not cadena:
            return True
        for i in cadena:
            int(i)
        return True
    except:
        return False

def crear_sufijo(cadena):
    retorno = ""
    try:
        if not cadena:
            return cadena
        entero = int(cadena)
        if entero < 10:
            retorno = "00" + str(entero)
        elif entero < 100:
            retorno = "0" + str(entero)
        else:
            retorno = str(entero)
        return retorno
    except:
        return cadena