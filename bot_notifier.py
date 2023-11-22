
from datetime import datetime
import requests
import numpy as np
from bot_database import sql_session
from sqlalchemy import exc


class Notifier():
    
    def __init__(self) -> None:
        
        #self.token = '5437213668:AAEoW6ErWWVHm81j7Jdi3-rzec2fUbNCIEI'
        #self.id_bot = '-1001865143871'
        self.token = '6332743294:AAFKcqzyfKzXAPSGhR6eTKLPMyx0tpCzeA4'
        # self.id_bot_aita = '-1001517241898'
        self.id_bot = '-1002027509507'
        self.id_error_bot = '-1002041194998'
        self.tables = {}
        self.total_equity = 0
        self.gorka_equity = 2000
        self.gorka_s = 0.5
        
        
    def send_order_placed(self, price, amount, symbol, action, id_, base_balance, asset_balance):
        
        message = ('#' + str(action) + '_PLACED' + '\n' + 
                   'Symbol: ' + str(symbol.name) + '\n' + 
                   'Price: ' + str(price) + '\n' + 
                   'Amount: ' + str(round(amount, 5)) + '\n' + 
                   'Cost: ' + str(round(amount*price, 2)) + '$' + '\n' + 
                   'Id: ' + str(id_))
        try:  
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_bot, 'text': message, 'parse_mode': 'HTML'})
            self.register_output('Action', symbol.asset, symbol.side, str(action) + ' placed')
        except Exception as e:
            print(str(action) + ' Placed Order Post Error')
            self.register_output('Error', symbol.asset, symbol.side, 'Order Placed Post Error: ' + str(e))
        
        return
    
    def send_open_order_filled(self, price, amount, symbol):
        
        message = ('#OPEN_FILLED' + '\n' + 
                   'Symbol: ' + str(symbol.name) + '\n' + 
                   'Price: ' + str(price) + '\n' + 
                   'Amount: ' + str(round(amount, symbol.master.account.amount_precision[symbol.asset])) + '\n' + 
                   'Cost: ' + str(round(symbol.acc, 2)) + '$' + '\n' +
                   'Average Point: ' + str(round(symbol.average_point, symbol.master.account.price_precision[symbol.asset])) + '\n' +
                   'Close Point: ' + str(round(symbol.close_point, symbol.master.account.price_precision[symbol.asset])))
        try:  
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_bot, 'text': message, 'parse_mode': 'HTML'})
            self.register_output('Action', symbol.asset, symbol.side, 'Open filled')
        except Exception as e:
            print('Open Order Post Error')
            self.register_output('Error', symbol.asset, symbol.side, 'Open Order Filled Post Error: ' + str(e))
        
        return
    
    def send_average_order_filled(self, price, amount, symbol, last_drop):
        
        message = ('#AVERAGING_FILLED' + '\n' + 
                   'Symbol: ' + str(symbol.name) + '\n' + 
                   'Buy Level: ' + str(symbol.buy_level) + '\n' +
                   'Drop: ' + str(abs(round(((price/symbol.open_price - 1) * 100), 2))) + '%' + '\n' +
                   'Last Drop: ' + str(round(last_drop, 2)) + '\n' +
                   'Price: ' + str(round(price, symbol.master.account.price_precision[symbol.asset])) + '\n' +
                   'Amount: ' + str(amount) + ' (' + str(round(amount*price, 2)) + '$) \n' + 
                   'Cost: ' + str(round(symbol.acc,2)) + '$' + '\n' +
                   'Average Price: ' + str(round(symbol.average_price, symbol.master.account.price_precision[symbol.asset])) + '\n' +
                   'Average Point: ' + str(round(symbol.average_point, symbol.master.account.price_precision[symbol.asset])) + '\n' +
                   'Close Point: ' + str(round(symbol.close_point, symbol.master.account.price_precision[symbol.asset])))
        try:  
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_bot, 'text': message, 'parse_mode': 'HTML'})
            self.register_output('Action', symbol.asset, symbol.side, 'Average filled')
        except Exception as e:
            print('Average Order Post Error')
            self.register_output('Error', symbol.asset, symbol.side, 'Average Order Filled Post Error: ' + str(e))
        
        return
    
    def send_transaction_closed_filled(self, symbol, profit, usd_profit, commission, price, covered):
        
        self.total_equity = self.total_equity + usd_profit        
        
        message = ('#OPERACION CERRADA' + '\n' + 
                   'Symbol: ' + str(symbol.name) + '\n' + 
                   'Coste: ' + str(round(symbol.acc,2)) + '$' + '\n' +
                   'Beneficio (%): ' + str(round(profit*100, 2)) + '% \n' + 
                   'Beneficio ($): ' + str(round(float(usd_profit), 3)) + '\n' +
                   '% Cubierto: ' + str(covered) + '\n' +
                   'Precio: ' + str(price) + '\n' +
                   'Duracion: ' + str(symbol.duration) + '\n' + 
                   'Nº de compras: ' + str(symbol.buy_level) + '\n' + 
                   'Comision ($): ' + str(np.around(commission, 5)) + '\n' +
                   'Beneficio Total: ' + str(np.around(self.total_equity, 2)))
        
        self.operation_client(usd_profit)
        try:
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_bot, 'text': message, 'parse_mode': 'HTML'})
            self.register_output('Action', symbol.asset, symbol.side, 'Close filled')
        except Exception as e:
            print('Transaction Closed Post Error')
            self.register_output('Error', symbol.asset, symbol.side, 'Transaction Closed Post Error: ' + str(e))
        return
    
    def operation_client(self, usd_profit):
        
        self.gorka_equity = self.gorka_equity + usd_profit*self.gorka_s      
        
        message = ('#OPERACION CERRADA GORKA' + '\n' + 
                   'Beneficio Gorka ($): ' + str(round(float(usd_profit)*self.gorka_s, 4)) + '\n' +
                   'Beneficio Total Gorka: ' + str(np.around(self.gorka_equity, 2)))
        try:
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_bot, 'text': message, 'parse_mode': 'HTML'})
        except Exception as e:
            print('Transaction Closed Post Error' + str(e))
        
        return
    
    def send_cancel_order(self, asset, side, action, id_):
        
        message = ('#CANCEL_ORDER_ ' + '\n' + 
                   'Asset: ' + str(asset) + '\n' + 
                   'Side: ' + str(side) + '\n' + 
                   'Action: ' + str(action) + '\n' + 
                   'Id: ' + str(id_))
        try:  
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_bot, 'text': message, 'parse_mode': 'HTML'})
            self.register_output('Cancel order', asset, side, str(action) + ' ' + str(id_))
        except Exception as e:
            print('Cancel Order Post Error')
            self.register_output('Error', asset, side, 'Cancel Order Post Error: ' + str(e))
        
        return
    
    def register_output(self, type_, asset, side, content):
        
        time = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, datetime.now().second)
        new_row = self.tables['output'](Date=str(time), Type=type_, Asset=asset, Side=side, Content=content)
        sql_session.add(new_row)
        try:
            sql_session.commit()
        except exc.OperationalError as e:
            print(f"Error de conexión a la base de datos: {e}")
            sql_session.rollback()  # Revertir cambios pendientes, si los hay
        return
    
    def start_trailing(self, price, symbol, tr_price, action):
        
        message = ('#START_TRAILING' + '\n' + 
                   'Symbol: ' + str(symbol.name) + '\n' + 
                   'Action: ' + str(action) + '\n' + 
                   'Price: ' + str(price) + '\n' + 
                   'Trailing Point: ' + str(round(tr_price, 2)))
        try:  
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_bot, 'text': message, 'parse_mode': 'HTML'})
        except Exception as e:
            print('Open Order Post Error' + str(e))
        
        return
    
    def send_error(self, symbol, error):
        
        message = ('#ERROR' + '\n' + 
                   'Account: ISOLATED \n' + 
                   'Symbol: ' + str(symbol) + '\n' + 
                   'Error: ' + error)
        try:  
            requests.post('https://api.telegram.org/bot' + self.token + '/sendMessage', data={'chat_id': self.id_error_bot, 'text': message, 'parse_mode': 'HTML'})
        except Exception as e:
            print('Send Error Post Error' + str(e))
        return
    
__all__ = ['Notifier']

    