define( ['lamelib/lame_widget'], function( lame_widget ) {

    $.widget( 'cool_widget', {
        options: {
            'secret_test': 100
        },

        _create: function() {
          this.a_number = 20;
        },

        b_function: function( bar ) {
            return {
                b_value: 'biz'
            };
        }
    } );

} );
