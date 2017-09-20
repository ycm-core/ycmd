// This file contains a usage of the global value 'global', but it does *not*
// appear in .tern-project's 'loadEagerly'. This means that it does not get
// renamed when we run the rename command.
window.eval( 'xyz' + global );

// Though it does if we tell tern about it.
