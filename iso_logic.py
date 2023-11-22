# -*- coding: utf-8 -*-
"""
Created on Fri Sep  8 17:09:12 2023

@author: gorka
"""

#LOGIC

import socket
import time
import requests
import pickle
import copy
from binance.exceptions import BinanceAPIException
from bot_symbol_combi import Symbol_combi
from bot_symbol_long import Symbol_long
from bot_symbol_short import Symbol_short
from bot_notifier import Notifier
from bot_account import Margin_account
from bot_database import init_database, sql_assets, sql_session
from sqlalchemy import delete
from sqlalchemy.exc import OperationalError


url = 'https://api.telegram.org/bot6332743294:AAFKcqzyfKzXAPSGhR6eTKLPMyx0tpCzeA4/sendMessage'

# inputs = [{'drop': 1, 'profit': 0.5, 'k': 1.2, 'buy_trail':0.25, 'sell_trail':0.15, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'},
#           {'drop': -1, 'profit': 0.5, 'k': 1.2, 'buy_trail':0.15, 'sell_trail':0.25, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'}]

inputs = [{'drop': 0.2, 'profit': 0.1, 'k': 1.2, 'buy_trail':0.05, 'sell_trail':0.05, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'},
          {'drop': -0.2, 'profit': 0.1, 'k': 1.2, 'buy_trail':0.05, 'sell_trail':0.05, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'}]

backup = False

if __name__ == '__main__':
    
    if backup:
        
        sql_tables = init_database(sql_assets, True)
        account = Margin_account(Notifier())
        account.notifier.tables = sql_tables
        
        master = Symbol_combi()
        master.account = account
        
        with open("master.pickle", "rb") as f:
            master_back = pickle.load(f)
        
        master.symbol_list = master_back
        for i in master.symbol_list:
            i.master = master

        master.init_params(True)  
        print('Backup charged')
        
    else:
    
        sql_tables = init_database(sql_assets, False)
        account = Margin_account(Notifier())
        account.notifier.tables = sql_tables
        
        master = Symbol_combi()
        master.account = account
        master.add_symbols(inputs)
        master.init_params(False)    
        print('System initialized')
    
    print('Start Operating')
    
    while True:
        
        if master.engine_working == True:
            
            try:
                master.update_open_tr()
                backup_list = copy.deepcopy(master.symbol_list)
                
                for i in backup_list:
                    i.master = []
                with open("master.pickle", "wb") as f:
                    pickle.dump(backup_list, f)
                    
            except BinanceAPIException as e:
                print(f"Se produjo un error de la API de Binance: {e}")
                master.account.notifier.register_output('Error', 'general', 'general', 'Binance API error ' + str(e))
                master.account.notifier.send_error('General', 'Binance API error ' + str(e))
            except requests.exceptions.ReadTimeout as e:
                print(f"Error de tiempo de espera en la API de Binance: {e}")
                master.account.notifier.register_output('Error', 'general', 'general', 'Binance API error ' + str(e))
                master.account.notifier.send_error('General', 'Binance API error ' + str(e))
            except OperationalError as e:
                # Captura el error específico de SQLAlchemy
                print(f"Error de conexión a la base de datos: {e}")
                master.account.notifier.send_error('General', f"Error de conexión a la base de datos: {e}")

            # except Exception as e:
            #     print(f"ERROR NO IDENTIFICADO: {e}")
            time.sleep(30)

            try: # Conectarse con frontend y pedir instrucciones
                logic_front_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                logic_front_socket.settimeout(5) # Esperar 5 segundos antes de ejecutar la lógica
                logic_front_socket.connect(('localhost', 5559))
                
                texto = 'Conexion success'
                mensaje = texto.encode('utf-8')
                logic_front_socket.send(mensaje)
                
                requests.post(url, data={'chat_id': '-1001802125737', 'text':  texto, 'parse_mode': 'HTML'})
                
                logic_front_socket.close()
                
                master.engine_working = False
                requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine stopped', 'parse_mode': 'HTML'})

            except socket.error as e:
                pass                
            except socket.timeout:
                pass

            except Exception as e:
                print('Error de logic al conectar frontend: ', str(e))
                requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Error de logic al conectar frontend: ' + str(e), 'parse_mode': 'HTML'})
                master.account.notifier.send_error('General', 'Error de logic al conectar frontend: ', str(e))
                # time.sleep(30)
            finally:
                logic_front_socket.close()

            
        elif master.engine_working == False:
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as front_server:
                front_server.bind(('localhost', 5558))
                front_server.listen(1)
                conexion, direccion = front_server.accept()
                
                try:
                    data = conexion.recv(1024)
                    texto = data.decode('utf-8')
                    requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Text received: ' + texto, 'parse_mode': 'HTML'})
                    time.sleep(2)
                
                    if 'SWITCH' in texto:
                        switch_data = conexion.recv(4096)
                        switch_params = pickle.loads(switch_data)
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'Side: ' + switch_params['side'] + ' Mode: ' + switch_params['mode'], 'parse_mode': 'HTML'})
                        
                        with open("master.pickle", "rb") as f:
                            master_back = pickle.load(f)
                            
                        master.symbol_list = master_back
                        for i in master.symbol_list:
                            i.master = master
                            
                        if switch_params['side'] == 'All':
                            if switch_params['mode'] == 'OFF':
                                for i in master.symbol_list:
                                    i.switch = False
                                    requests.post(url, data={'chat_id': '-1001802125737', 'text':  i.name + 'turned  ' + str(i.switch), 'parse_mode': 'HTML'})
                            elif switch_params['mode'] == 'ON':
                                for i in master.symbol_list:
                                    i.switch = True
                                    requests.post(url, data={'chat_id': '-1001802125737', 'text':  i.name + 'turned  ' + str(i.switch), 'parse_mode': 'HTML'})
                                    
                        elif switch_params['side'] == 'Long':
                            if switch_params['mode'] == 'OFF':
                                for i in master.symbol_list:
                                    if i.side == 'Long':
                                        i.switch = False
                                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  i.name + 'turned  ' + str(i.switch), 'parse_mode': 'HTML'})

                            elif switch_params['mode'] == 'ON':
                                for i in master.symbol_list:
                                    if i.side == 'Long':
                                        i.switch = True
                                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  i.name + 'turned  ' + str(i.switch), 'parse_mode': 'HTML'})

                        elif switch_params['side'] == 'Short':
                            if switch_params['mode'] == 'OFF':
                                for i in master.symbol_list:
                                    if i.side == 'Short':
                                        i.switch = False
                                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  i.name + 'turned  ' + str(i.switch), 'parse_mode': 'HTML'})

                            elif switch_params['mode'] == 'ON':
                                for i in master.symbol_list:
                                    if i.side == 'Short':
                                        i.switch = True
                                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  i.name + 'turned  ' + str(i.switch), 'parse_mode': 'HTML'})

                        restart_symbols = delete(master.account.notifier.tables['symbols'])
                        sql_session.execute(restart_symbols)
                        for symbol in master.symbol_list:
                            new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Drop_param=symbol.drop_param, Level=symbol.level, Pond=symbol.pond, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
                            sql_session.add(new_row)
                        sql_session.commit()
    
                        master.engine_working = True
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'Engine started (switch)', 'parse_mode': 'HTML'})
                        conexion.close()
    
                    elif 'EDIT SYMBOL' in texto:
                        edit_symbol_data = conexion.recv(4096)
                        edit_params = pickle.loads(edit_symbol_data)
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'Name: ' + edit_params['name'] + ' Attribute: ' + edit_params['attribute'] + ' Value: ' + str(edit_params['value']), 'parse_mode': 'HTML'})
                        
                        
                        with open("master.pickle", "rb") as f:
                            symbol_list = pickle.load(f)
                        
                        selected_symbol = next(symbol for symbol in symbol_list if symbol.name == edit_params['name'])
                        mapeo = {'Drop': 'drop', 'TP': 'profit', 'K': 'k', 'Buy Trail': 'buy_trail', 'Sell Trail': 'sell_trail', 'Drop Param':'drop_param', 'Level': 'level', 'Pond': 'pond',
                                    'Switch': 'switch', 'Status': 'status', 'Can Open': 'can_open', 'Can Average': 'can_average', 'Can Close': 'can_close', 
                                    'Can Open Trail': 'can_open_trail', 'Can Average Trail': 'can_average_trail', 'Can Close Trail': 'can_close_trail'}
                        
                        if edit_params['attribute'] in mapeo:
                            attribute_name = mapeo[edit_params['attribute']]
                            if attribute_name in ['switch', 'status', 'can_open', 'can_average', 'can_close', 'can_open_trail', 'can_average_trail', 'can_close_trail']:
                                setattr(selected_symbol, attribute_name, bool(int(edit_params['value'])))
                            else:
                                setattr(selected_symbol, attribute_name, edit_params['value'])
                        
                        warn = 'Changed completed ' + 'Symbol: ' + selected_symbol.name + 'Param: ' + str(attribute_name) + 'New Value: ' + str(selected_symbol.drop_param)
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': warn, 'parse_mode': 'HTML'})
                        

                        master.symbol_list = symbol_list                           
                        for i in master.symbol_list:
                            i.master = master
                            i.trading_points()
                            requests.post(url, data={'chat_id': '-1001802125737', 'text': attribute_name + str(i.drop_param), 'parse_mode': 'HTML'})

                        restart_symbols = delete(master.account.notifier.tables['symbols'])
                        sql_session.execute(restart_symbols)
                        for symbol in master.symbol_list:
                            new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Drop_param=symbol.drop_param, Level=symbol.level, Pond=symbol.pond, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
                            sql_session.add(new_row)
                        sql_session.commit()                    
        
                        master.engine_working = True
                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine started (edit)', 'parse_mode': 'HTML'})
                        conexion.close()
    
                    elif 'ADD SYMBOL' in texto:
                        add_symbol_data = conexion.recv(4096)
                        add_symbol_params = pickle.loads(add_symbol_data)
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'Drop: ' + str(add_symbol_params[0]['drop']) + ' Profit: ' + str(add_symbol_params[0]['profit']) + ' K: ' + str(add_symbol_params[0]['k']), 'parse_mode': 'HTML'})
                        
                        with open("master.pickle", "rb") as f:
                            master_back = pickle.load(f)
                            
                        master.symbol_list = master_back
                        for i in master.symbol_list:
                            i.master = master
                        
                        master.add_new_symbol(add_symbol_params)
    
                        restart_symbols = delete(master.account.notifier.tables['symbols'])
                        sql_session.execute(restart_symbols)
                        for symbol in master.symbol_list:
                            new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Drop_param=symbol.drop_param, Level=symbol.level, Pond=symbol.pond, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
                            sql_session.add(new_row)
                        sql_session.commit()      
    
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'New symbol added', 'parse_mode': 'HTML'})
                        master.engine_working = True
                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine started (add)', 'parse_mode': 'HTML'})
                        conexion.close()

                except socket.error:
                    pass
                except socket.timeout:
                    pass
                
                finally:
                    conexion.close()