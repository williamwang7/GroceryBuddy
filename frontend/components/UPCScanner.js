import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { BarCodeScanner, Permissions } from 'expo';

/**
 * Class representing item addition form for adding items.
 * @extends React.Component
 */
export default class ItemAdditionForm extends React.Component {
  static navigationOptions = () => ({
    title: 'Scan Bar Code',
  })

  /**
   * Creates the ItemAdditionForm
   * @param {object} props
   */
  constructor(props) {
    super(props);

    this.state = {
      hasCameraPermission: null,
    };
  }

  async componentDidMount() {
    const { status } = await Permissions.askAsync(Permissions.CAMERA);
    this.setState({ hasCameraPermission: status === 'granted' });
  }

  /**
   * Sends the barcode back to the original router
   * @param  {string} {type - type of barcode
   * @param  {object} data} - barcode data
   */
  handleBarCodeScanned = ({ type, data }) => {
    this.props.navigation.goBack();
    this.props.navigation.getParam('handleBarCodeScanned')(type, data);
  }

  /**
   * renders scanner
   *
   * @return rendered scanner
   */
  render() {
    const { hasCameraPermission } = this.state;

    if (hasCameraPermission === null) {
      return <Text>Requesting for camera permission</Text>;
    }
    if (hasCameraPermission === false) {
      return <Text>No access to camera</Text>;
    }
    return (
      <View style={{ flex: 1 }}>
        <BarCodeScanner
          onBarCodeScanned={this.handleBarCodeScanned}
          style={StyleSheet.absoluteFill}
        />
      </View>
    );
  }
}
