update product_ubication 
set qty = stock_move.product_qty
from stock_move, ubication
where stock_move.product_id = product_ubication.product_id and stock_move.ubication_id = product_ubication.ubication_id;
