# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

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