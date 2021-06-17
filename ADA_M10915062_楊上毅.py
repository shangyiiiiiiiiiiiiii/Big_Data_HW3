class Strategy():
    # option setting needed
    def __setitem__(self, key, value):
        self.options[key] = value

    # option setting needed
    def __getitem__(self, key):
        return self.options.get(key, '')

    def __init__(self):
        # strategy property
        self.subscribedBooks = {
            'Binance': {
                'pairs': ['ADA-USDT'],
            },
        }
        # 4 * 60 * 60 sec ( 4hr )
        self.period = 4 * 60 * 60
        self.options = {}

        # user defined class attribute
        self.last_type = 'sell'
        self.last_cross_status = None
        self.close_price_trace = np.array([])


        self.OBV_trace = np.array([]) 
        self.acc_OBV = 0                        # saving accumulation OBV ( current OBV )
        self.OBV_UP = 1                         # buying at right time
        self.OBV_DOWN = 2                   # selling at right time
        self.stop_loss = 0
        self.lockin_gain = 0

        
        self.ma_long = 21
        self.ma_medium = 12
        self.ma_short = 3
        self.MA_UP = 1
        self.MA_DOWN = 2


    def on_order_state_change(self,  order):
        Log("on order state change message: " + str(order) + " order price: " + str(order["price"]))

    def get_current_ma_cross(self):
        s_ma = talib.SMA(self.close_price_trace, self.ma_short)[-1]
        m_ma = talib.SMA(self.close_price_trace, self.ma_medium)[-1]
        l_ma = talib.SMA(self.close_price_trace, self.ma_long)[-1]


        self.stop_loss = l_ma
        self.lockin_gain = l_ma * 1.15


        if np.isnan(s_ma) or np.isnan(m_ma):
            return None
        if s_ma > m_ma:
            return self.MA_UP
        return self.MA_DOWN


    def get_OBV_cross(self):
        OBV_ma =  talib.SMA( self.OBV_trace, self.ma_medium)[-1]
        Log('OBV_ma = ' + str(OBV_ma))
        Log('OBV =  ' + str(self.OBV_trace[-1]))
        if np.isnan(OBV_ma):
            return None
        if self.OBV_trace[-1] > OBV_ma:
            return self.OBV_UP
        return self.OBV_DOWN


    # called every self.period
    def trade(self, information):
        exchange = list(information['candles'])[0]                #Binance
        pair = list(information['candles'][exchange])[0]        #ADA-USDT
        target_currency = pair.split('-')[0]                             #ADA
        base_currency = pair.split('-')[1]                              #USDT

        base_currency_amount = self['assets'][exchange][base_currency] 
        target_currency_amount = self['assets'][exchange][target_currency]


        # add latest price into trace (ADA latest price)
        close_price = information['candles'][exchange][pair][0]['close']

        open_price = information['candles'][exchange][pair][0]['open']
        get_volume = information['candles'][exchange][pair][0]['volume']
        highest_price = information['candles'][exchange][pair][0]['high']
        lowest_price = information['candles'][exchange][pair][0]['low']

        ratio = ((close_price - lowest_price) - (highest_price -  close_price ))/ (highest_price - lowest_price)
        self.acc_OBV = self.acc_OBV + get_volume * ratio
        self.OBV_trace = np.append(self.OBV_trace, [float(self.acc_OBV)])
        self.OBV_trace = self.OBV_trace[-self.ma_long:]
        OBV_cross = self.get_OBV_cross()

        Log('The OBV state :  ' + str(OBV_cross)) 


        self.close_price_trace = np.append(self.close_price_trace, [float(close_price)])
        # only keep max length of ma_long count elements(i.e. last 5 day)
        self.close_price_trace = self.close_price_trace[-self.ma_long:]
        # calculate current ma cross status
        cur_cross = self.get_current_ma_cross()


        if cur_cross is None:
            return []
        if self.last_cross_status is None:
            self.last_cross_status = cur_cross
            return []

        # stop loss
        if self.stop_loss >= close_price:
            Log('stop loss selling: ' + str(self['assets'][exchange][base_currency]))
            self.last_type = 'sell'
            self.last_cross_status = cur_cross
            return [
                {
                    'exchange': exchange,
                    'amount': -target_currency_amount,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]

            if self.lockin_gain <= close_price:
                Log('lock in gain selling: ' + str(self['assets'][exchange][base_currency]))
                self.last_type = 'sell'
                self.last_cross_status = cur_cross
                return [
                    {
                        'exchange': exchange,
                        'amount': -target_currency_amount,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
        
        # cross up(from down to up)
        if self.last_type == 'sell' and cur_cross == self.MA_UP and self.last_cross_status == self.MA_DOWN:
            if OBV_cross == self.OBV_UP:
                Log('buying 50000 unit of ' + str(target_currency))
                self.last_type = 'buy'
                self.last_cross_status = cur_cross
                return [
                    {
                        'exchange': exchange,
                        'amount': 50000,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
            elif OBV_cross == self.OBV_DOWN:
                Log('buying 10000 unit of ' + str(target_currency))
                self.last_type = 'buy'
                self.last_cross_status = cur_cross
                return [
                    {
                        'exchange': exchange,
                        'amount': 10000,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
            
        # cross down(from up to down)
        elif self.last_type == 'buy' and cur_cross == self.MA_DOWN and self.last_cross_status == self.MA_UP:
            if OBV_cross == self.OBV_UP:
                Log('selling 20000 unit of ' + str(target_currency))
                self.last_type = 'sell'
                self.last_cross_status = cur_cross
                return [
                    {
                        'exchange': exchange,
                        'amount': -20000,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
            ]
            elif OBV_cross == self.OBV_DOWN:
                Log('assets before selling: ' + str(self['assets'][exchange][base_currency]))
                self.last_type = 'sell'
                self.last_cross_status = cur_cross
                return [
                    {
                        'exchange': exchange,
                        'amount': -target_currency_amount,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]

        self.last_cross_status = cur_cross
        return []