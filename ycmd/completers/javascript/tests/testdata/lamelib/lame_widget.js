define( ['lamelib/lame_widget'], function( lame_widget ) {

    $.widget( 'cool_widget', {

        options: {
            'test': 200
        },

        a_function: function( bar ) {
            return {
                a_value: 'baz'
            }
        }

     );

} );
