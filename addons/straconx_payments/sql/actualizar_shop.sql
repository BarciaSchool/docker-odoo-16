update account_bank_statement set shop_id = (select shop_id from printer_point where printer_id = printer_point.id);
