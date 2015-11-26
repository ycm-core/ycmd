define( ['lamelib/lame_widget'], function( lame_widget ) {

    $.widget( 'cool_widget', {

        options: {
            'test': 100
        }


        b_function: function( bar ) {
            return {
                b_value: 'biz'
            }
        }
     );

} );
