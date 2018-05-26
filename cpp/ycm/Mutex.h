#ifndef YCM_MUTEX_H
#define YCM_MUTEX_H

#include <mutex>

// Enable thread safety attributes only with clang.
// The attributes can be safely erased when compiling with other compilers.
#if defined( __clang__ ) && ( !defined( SWIG ) )
#define THREAD_ANNOTATION_ATTRIBUTE__( x )   __attribute__( ( x ) )
#else
#define THREAD_ANNOTATION_ATTRIBUTE__( x )   // no-op
#endif

#define CAPABILITY( x ) THREAD_ANNOTATION_ATTRIBUTE__( capability( x ) )

#define SCOPED_CAPABILITY THREAD_ANNOTATION_ATTRIBUTE__( scoped_lockable )

#define GUARDED_BY( x ) THREAD_ANNOTATION_ATTRIBUTE__( guarded_by( x ) )

#define PT_GUARDED_BY( x ) THREAD_ANNOTATION_ATTRIBUTE__( pt_guarded_by( x ) )

#define ACQUIRED_BEFORE( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( acquired_before( __VA_ARGS__ ) )

#define ACQUIRED_AFTER( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( acquired_after( __VA_ARGS__ ) )

#define REQUIRES( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( requires_capability( __VA_ARGS__ ) )

#define REQUIRES_SHARED( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( requires_shared_capability( __VA_ARGS__ ) )

#define ACQUIRE( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( acquire_capability( __VA_ARGS__ ) )

#define ACQUIRE_SHARED( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( acquire_shared_capability( __VA_ARGS__ ) )

#define RELEASE( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( release_capability( __VA_ARGS__ ) )

#define RELEASE_SHARED( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( release_shared_capability( __VA_ARGS__ ) )

#define TRY_ACQUIRE( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( try_acquire_capability( __VA_ARGS__ ) )

#define TRY_ACQUIRE_SHARED( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( try_acquire_shared_capability( __VA_ARGS__ ) )

#define EXCLUDES( ... ) \
  THREAD_ANNOTATION_ATTRIBUTE__( locks_excluded( __VA_ARGS__ ) )

#define ASSERT_CAPABILITY( x ) \
  THREAD_ANNOTATION_ATTRIBUTE__( assert_capability( x ) )

#define ASSERT_SHARED_CAPABILITY( x ) \
  THREAD_ANNOTATION_ATTRIBUTE__( assert_shared_capability( x ) )

#define RETURN_CAPABILITY( x ) \
  THREAD_ANNOTATION_ATTRIBUTE__( lock_returned( x ) )

#define NO_THREAD_SAFETY_ANALYSIS \
  THREAD_ANNOTATION_ATTRIBUTE__( no_thread_safety_analysis )

namespace YouCompleteMe {

// NOTE: Wrappers for std::mutex, std::lock_guard andstd::unique_lock
// are provided so that we can annotate them with thread safety attributes
// and use the -Wthread-safety warning with clang.
// The standard library types cannot be
// used directly because they do not provided the required annotations.
class CAPABILITY( "mutex" ) Mutex {
 public:
  Mutex() = default;

  void lock() ACQUIRE() { mut_.lock(); }
  void unlock() RELEASE() { mut_.unlock(); }
  std::mutex &native_handle() { return mut_; }

 private:
  std::mutex mut_;
};


template <class LockType>
class SCOPED_CAPABILITY LockWrapper {
public:
  LockWrapper( Mutex &m ) ACQUIRE( m ) : lt_( m.native_handle() ) {}

  template < typename T = LockType, typename std::enable_if<
    std::is_same< T, std::unique_lock< std::mutex > >::value, int >::type = 0 >
  LockWrapper( Mutex &m, std::try_to_lock_t ) ACQUIRE( m )
    : lt_( m.native_handle(), std::try_to_lock ) {}

  ~LockWrapper() RELEASE() = default;
  template < typename T = LockType, typename std::enable_if<
    std::is_same< T, std::unique_lock< std::mutex > >::value, int >::type = 0 >
  bool owns_lock() { return lt_.owns_lock(); }
private:
  LockType lt_;
};

} // namespace YouCompleteMe

#endif
