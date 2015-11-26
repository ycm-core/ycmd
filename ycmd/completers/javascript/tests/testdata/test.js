
define( [ 'coollib/cool_widget', 'coollib/cool_object' ],
        function( cool_widget, cool_object ) {

    $('<div>').cool_widget( { test: 300 } );

    var x = {
        'test': 100,

        // This is a test function. It isn't 
        //
        // very
        //
        // usefl
        'not_test': function( test, test1 ) {
            return 'test'
        }
    };

    cool_object.mine_bitcoin( 300 );
    cool_object.mine_bitcoin( 200 );

    x.not_test();

    

} );
