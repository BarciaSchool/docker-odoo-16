
def sequence_change(line_ids=[], shop=None, context=None):
    try:
        vals = []
        sequence = 1
        if line_ids:
            for tup in line_ids:
                line_data = tup[2]
                if line_data:
                    dato = line_data['sequence']
                    vals.append(dato)
            while True:
                b=False
                for sec in vals:
                    if sequence == sec:
                        b=True
                if b:
                    sequence +=1
                else:
                    break
        if sequence > shop.limits_line_invoice:
            return False
        return sequence
    except:
        return False