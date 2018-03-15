echo "Downloading pretrained vision model..."
url=http://i.stanford.edu/hazy/share/fonduer/visualtable/pretrained-model.tar.gz
data_tar=pretrained-model
if type curl &>/dev/null; then
    curl -RLO $url
elif type wget &>/dev/null; then
    wget -N -nc $url
fi
echo "Unpacking pretrained model..."
tar -zxvf $data_tar.tar.gz -C .
echo "Deleting tar file..."
rm $data_tar.tar.gz

echo "Done!"
