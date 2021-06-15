// Copyright (C) 2011-2018 ycmd contributors
//
// This file is part of ycmd.
//
// ycmd is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// ycmd is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

#ifndef UTILS_H_KEPMRPBH
#define UTILS_H_KEPMRPBH

#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <filesystem>
#include <future>
#include <limits>
#include <mutex>
#include <queue>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <vector>

namespace fs = std::filesystem;

namespace YouCompleteMe {

YCM_EXPORT inline bool IsUppercase( uint8_t ascii_character ) {
  return 'A' <= ascii_character && ascii_character <= 'Z';
}


// An uppercase ASCII character can be converted to lowercase and vice versa by
// flipping its third most significant bit.
YCM_EXPORT inline char Lowercase( uint8_t ascii_character ) {
  if ( IsUppercase( ascii_character ) ) {
    return static_cast< char >( ascii_character ^ 0x20 );
  }
  return static_cast< char >( ascii_character );
}


YCM_EXPORT inline std::string Lowercase( std::string_view text ) {
  std::string result( text.size(), '\0' );
  std::transform( text.begin(),
                  text.end(),
                  result.begin(),
                  []( char c ) {
                    return Lowercase( static_cast< uint8_t >( c ) );
                  } );
  return result;
}


// Reads the entire contents of the specified file. If the file does not exist,
// an exception is thrown.
std::vector< std::string > ReadUtf8File( const fs::path &filepath );


template <class Container, class Key, typename Value>
typename Container::mapped_type &
GetValueElseInsert( Container &container,
                    Key&& key,
                    Value&& value ) {
  return container.try_emplace(
    std::forward< Key >( key ), std::forward< Value >( value ) ).first->second;
}


template<typename C, typename = void>
struct is_associative : std::false_type {};

template<typename C>
struct is_associative<C, std::void_t<typename C::mapped_type>> : std::true_type {};

template <class Container, class Key, class Ret>
Ret
FindWithDefault( Container &container,
                 const Key &key,
                 Ret&& value ) {
  typename Container::const_iterator it = [ &key ]( auto&& c ) {
    if constexpr ( is_associative<Container>::value ) {
      return c.find( key );
    } else {
      return std::find_if( c.begin(), c.end(), [ &key ]( auto&& p ) {
          return p.first == key; } );
    }
  }( container );
  if ( it != container.end() ) {
    return Ret{ it->second };
  }
  return std::move( value );
}


template <class Container, class Key>
bool Erase( Container &container, const Key &key ) {
  typename Container::iterator it = container.find( key );

  if ( it != container.end() ) {
    container.erase( it );
    return true;
  }

  return false;
}


class ThreadPool {
public:
  explicit ThreadPool( size_t n = 2 * std::thread::hardware_concurrency() )
    : threads_( n ),
      stop_( false ) {
    for( auto&& t : threads_ ) {
      t = std::thread( &ThreadPool::thread_loop, this );
    }
  }

  // TODO: Rule of five?
  ~ThreadPool() {
    stop_.store( true, std::memory_order_release );
    cv_.notify_all();
    for( auto& t : threads_ ) {
      t.join();
    }
  }

  template< typename F, typename...Args >
  std::future< std::invoke_result_t< F, Args... > > push( F&& f, Args&&...args ) {
    // We need the future associated with this packaged_task.
    // That means we can't move the packaged_task itself into the queue.
    // Hence, the unique_ptr< packaged_task< return_type > >.
    auto task = std::make_unique< std::packaged_task< std::invoke_result_t< F, Args... >() > >(
        std::bind(std::forward< F >( f ), std::forward< Args >( args )...) );
    std::future< std::invoke_result_t< F, Args... > > future = task->get_future();
    {
      std::lock_guard lock{ queued_tasks_mutex_ };
      // Using release() because std::function requires a copyable type
      // but also because trivial copyability is needed to avoid allocations.
      queued_tasks_.push( [ task = task.release() ] {
          ( *task )();
          delete task;
      } );
    }
    cv_.notify_one();
    return future;
  }

private:
  void thread_loop() {
    while( 1 ) {
      std::function< void() > task;
      {
        std::unique_lock lock{ queued_tasks_mutex_ };
        cv_.wait( lock, [ this ]{
            return !queued_tasks_.empty() ||
                   stop_.load( std::memory_order_acquire );
        } );
        if ( stop_.load( std::memory_order_relaxed ) ) {
          // We need to drain the queue somehow.
          // This is draining the queue in a single thread.
          // Is there a better way?
          // Is it okay to be slow at shutdown?
          while( !queued_tasks_.empty() ) {
            queued_tasks_.front()();
            queued_tasks_.pop();
          }
          return;
        }
        task = std::move( queued_tasks_.front() );
        queued_tasks_.pop();
      }
      task();
    }
  }

  std::vector< std::thread > threads_;
  std::queue< std::function< void() > > queued_tasks_;
  std::mutex queued_tasks_mutex_;
  std::condition_variable cv_;
  std::atomic_bool stop_; // Really a job for stop_token/jthread.
};
// TODO: Should this be a singleton instead?
// Or just a free function that returns an instance?


inline ThreadPool tasks;
// Shrink a vector to its sorted |num_sorted_elements| smallest elements. If
// |num_sorted_elements| is 0 or larger than the vector size, sort the whole
// vector.
template <typename Element>
void PartialSort( std::vector< Element > &elements,
                  const size_t num_sorted_elements ) {

  using diff = typename std::vector< Element >::iterator::difference_type;
  size_t nb_elements = elements.size();
  size_t max_elements = num_sorted_elements > 0 &&
                        nb_elements >= num_sorted_elements ?
                        num_sorted_elements : nb_elements;

  // When the number of elements to sort is more than 1024 and one sixty-fourth
  // of the total number of elements, switch to std::nth_element followed by
  // std::sort. This heuristic is based on the observation that
  // std::partial_sort (heapsort) is the most efficient algorithm when the
  // number of elements to sort is small and that std::nth_element (introselect)
  // combined with std::sort (introsort) always perform better than std::sort
  // alone in other cases.
  if ( max_elements <= std::max( static_cast< size_t >( 1024 ),
                                 nb_elements / 64 ) ) {
    std::partial_sort( elements.begin(),
                       elements.begin() + static_cast< diff >( max_elements ),
                       elements.end() );
  } else if ( 256 <= std::min( nb_elements, max_elements ) ) {
    // Should this be extracted into ParallelSort instead?
    const auto real_begin = elements.begin();
    const auto real_end = elements.end();
    const auto n_threads = std::thread::hardware_concurrency();
    const auto chunk_size = max_elements / n_threads;
    std::vector< std::future< void > > futures( n_threads );
    std::mutex cv_mutex;
    std::condition_variable cv;
    std::vector< bool > finished( n_threads );
    for ( auto i = 0u; i < n_threads; ++i ) {
      auto begin = real_begin + i * chunk_size;
      auto end = real_end - begin < static_cast< diff >( chunk_size ) ? real_end : begin + chunk_size;
      futures[i] = tasks.push(
        [ &, i ] ( auto begin, auto end ) {
          std::sort( begin, end );
          if ( i % 2 == 0 ) {
            unsigned next_wait = 1;
            do {
              if ( i + next_wait > n_threads - 1 ) {
                break;
              }
              {
                // This might be better served by a semaphore.
                // That's C++20 and a naive semaphore built on atmoics is
                // about as good as this thing.
                std::unique_lock lock{ cv_mutex };
                cv.wait( lock, [ &finished, i, next_wait ] {
                  return finished[ i + next_wait ] == true;
                } );
              }
              auto middle = begin + chunk_size * next_wait;
              end = begin + chunk_size * next_wait * 2;
              std::inplace_merge( begin, middle, end );
            // TODO: Boris, mind explaining this magic?
            } while( ~i & ( next_wait <<= 1 ) );
          }
          {
              std::unique_lock lock{ cv_mutex };
              finished[ i ] = true;
          }
          cv.notify_all();
        }, begin, end );
    }
    for ( auto&& f : futures ) { f.get(); }
  } else {
    std::nth_element( elements.begin(),
                      elements.begin() + static_cast< diff >( max_elements ),
                      elements.end() );
    std::sort( elements.begin(), elements.begin() + static_cast< diff >( max_elements ) );
  }

  // Remove the unsorted elements. Use erase instead of resize as it doesn't
  // require a default constructor on Element.
  elements.erase( elements.begin() + static_cast< diff >( max_elements ),
                  elements.end() );
}

} // namespace YouCompleteMe

#endif /* end of include guard: UTILS_H_KEPMRPBH */
