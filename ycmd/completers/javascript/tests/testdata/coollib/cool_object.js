define( [], function() {
    return {
        /**
         * This function takes a number and invests it in bitcoin. It returns
         * the expected value (in notional currency) after 1 year.
         */
        mine_bitcoin: function( how_much ) {
            return how_much * 0.001;
        }
    }
} )
