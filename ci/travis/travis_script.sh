if [ "${YCM_BENCHMARK}" == "true" ]; then
  ./benchmark.py
else
  ./run_tests.py
fi
